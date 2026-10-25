"""
Trace Search Query Service.
Searches and aggregates traces across tenant boundaries using PostgreSQL 16 aggregation,
computing span counts, total durations, root service names, and error statuses.
"""

import base64
from dataclasses import dataclass
from typing import List, Optional, Tuple
from sqlalchemy import select, func, case, desc, asc, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from storage.models import SpanRecord

@dataclass
class TraceSearchResult:
    trace_id: str
    root_name: str
    root_service: str
    start_time_unix_nano: int
    duration_nanos: int
    span_count: int
    has_errors: bool

@dataclass
class TraceAggregationResult:
    total_traces: int
    error_traces: int
    error_rate: float
    avg_duration_nanos: float
    min_duration_nanos: int
    max_duration_nanos: int
    total_spans: int
    avg_spans_per_trace: float

class TraceSearchService:
    async def search_traces(
        self,
        session: AsyncSession,
        tenant_id: str,
        service_name: Optional[str] = None,
        operation_name: Optional[str] = None,
        status_code: Optional[str] = None,
        min_duration_ns: Optional[int] = None,
        max_duration_ns: Optional[int] = None,
        min_time_ns: Optional[int] = None,
        max_time_ns: Optional[int] = None,
        attribute_filter: Optional[dict] = None,
        tag_key: Optional[str] = None,
        query_text: Optional[str] = None,
        order_by: str = "start_time",
        order_dir: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> List[TraceSearchResult]:
        where_clauses = [SpanRecord.tenant_id == tenant_id]
        if service_name:
            subq = (
                select(SpanRecord.trace_id)
                .where(SpanRecord.tenant_id == tenant_id, SpanRecord.service_name == service_name)
                .distinct()
            )
            where_clauses.append(SpanRecord.trace_id.in_(subq))

        if operation_name:
            subq = (
                select(SpanRecord.trace_id)
                .where(SpanRecord.tenant_id == tenant_id, SpanRecord.name == operation_name)
                .distinct()
            )
            where_clauses.append(SpanRecord.trace_id.in_(subq))

        if status_code:
            subq = (
                select(SpanRecord.trace_id)
                .where(SpanRecord.tenant_id == tenant_id, SpanRecord.status_code == status_code)
                .distinct()
            )
            where_clauses.append(SpanRecord.trace_id.in_(subq))

        if attribute_filter:
            for k, v in attribute_filter.items():
                subq = (
                    select(SpanRecord.trace_id)
                    .where(
                        SpanRecord.tenant_id == tenant_id,
                        SpanRecord.attributes.contains({k: v})
                    )
                    .distinct()
                )
                where_clauses.append(SpanRecord.trace_id.in_(subq))

        if tag_key:
            subq = (
                select(SpanRecord.trace_id)
                .where(
                    SpanRecord.tenant_id == tenant_id,
                    SpanRecord.attributes.has_key(tag_key)
                )
                .distinct()
            )
            where_clauses.append(SpanRecord.trace_id.in_(subq))

        if query_text:
            pattern = f"%{query_text}%"
            subq = (
                select(SpanRecord.trace_id)
                .where(
                    SpanRecord.tenant_id == tenant_id,
                    or_(
                        SpanRecord.name.ilike(pattern),
                        SpanRecord.service_name.ilike(pattern),
                        SpanRecord.status_message.ilike(pattern)
                    )
                )
                .distinct()
            )
            where_clauses.append(SpanRecord.trace_id.in_(subq))

        if min_time_ns is not None:
            where_clauses.append(SpanRecord.start_time_unix_nano >= min_time_ns)
        if max_time_ns is not None:
            where_clauses.append(SpanRecord.start_time_unix_nano <= max_time_ns)

        # Ordering expression
        order_col_name = "start_time"
        if order_by == "duration":
            order_col_name = "trace_duration"
        elif order_by == "span_count":
            order_col_name = "span_count"

        order_expr = asc(order_col_name) if order_dir.lower() == "asc" else desc(order_col_name)

        # Group spans by trace_id to calculate aggregated metrics
        agg_stmt = (
            select(
                SpanRecord.trace_id,
                func.min(SpanRecord.start_time_unix_nano).label("start_time"),
                func.max(SpanRecord.end_time_unix_nano).label("end_time"),
                func.count().label("span_count"),
                func.bool_or(SpanRecord.status_code == "ERROR").label("has_errors"),
                (func.max(SpanRecord.end_time_unix_nano) - func.min(SpanRecord.start_time_unix_nano)).label("trace_duration")
            )
            .where(*where_clauses)
            .group_by(SpanRecord.trace_id)
            .order_by(order_expr, desc(SpanRecord.trace_id))
            .limit(limit)
            .offset(offset)
        )

        # Apply duration HAVING filters
        if min_duration_ns is not None:
            agg_stmt = agg_stmt.having(
                (func.max(SpanRecord.end_time_unix_nano) - func.min(SpanRecord.start_time_unix_nano)) >= min_duration_ns
            )
        if max_duration_ns is not None:
            agg_stmt = agg_stmt.having(
                (func.max(SpanRecord.end_time_unix_nano) - func.min(SpanRecord.start_time_unix_nano)) <= max_duration_ns
            )

        rows = (await session.execute(agg_stmt)).all()
        results: List[TraceSearchResult] = []

        for row in rows:
            trace_id = row.trace_id
            start_time = row.start_time
            end_time = row.end_time
            span_count = row.span_count
            has_errors = bool(row.has_errors)
            duration = max(0, end_time - start_time)

            # Query the root or earliest span to get root_name and root_service
            root_stmt = (
                select(SpanRecord.name, SpanRecord.service_name)
                .where(
                    SpanRecord.tenant_id == tenant_id,
                    SpanRecord.trace_id == trace_id
                )
                .order_by(
                    case((SpanRecord.parent_span_id.is_(None), 0), else_=1),
                    SpanRecord.start_time_unix_nano.asc()
                )
                .limit(1)
            )
            root_row = (await session.execute(root_stmt)).first()
            root_name = root_row[0] if root_row else "unknown"
            root_service = root_row[1] if root_row else "unknown"

            results.append(
                TraceSearchResult(
                    trace_id=trace_id,
                    root_name=root_name,
                    root_service=root_service,
                    start_time_unix_nano=start_time,
                    duration_nanos=duration,
                    span_count=span_count,
                    has_errors=has_errors
                )
            )

        return results

    async def search_traces_cursor(
        self,
        session: AsyncSession,
        tenant_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        service_name: Optional[str] = None,
        operation_name: Optional[str] = None,
        status_code: Optional[str] = None,
        min_duration_ns: Optional[int] = None,
        max_duration_ns: Optional[int] = None,
        attribute_filter: Optional[dict] = None,
        tag_key: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> Tuple[List[TraceSearchResult], Optional[str]]:
        where_clauses = [SpanRecord.tenant_id == tenant_id]

        if service_name:
            subq = select(SpanRecord.trace_id).where(SpanRecord.tenant_id == tenant_id, SpanRecord.service_name == service_name).distinct()
            where_clauses.append(SpanRecord.trace_id.in_(subq))
        if operation_name:
            subq = select(SpanRecord.trace_id).where(SpanRecord.tenant_id == tenant_id, SpanRecord.name == operation_name).distinct()
            where_clauses.append(SpanRecord.trace_id.in_(subq))
        if status_code:
            subq = select(SpanRecord.trace_id).where(SpanRecord.tenant_id == tenant_id, SpanRecord.status_code == status_code).distinct()
            where_clauses.append(SpanRecord.trace_id.in_(subq))

        agg_stmt = (
            select(
                SpanRecord.trace_id,
                func.min(SpanRecord.start_time_unix_nano).label("start_time"),
                func.max(SpanRecord.end_time_unix_nano).label("end_time"),
                func.count().label("span_count"),
                func.bool_or(SpanRecord.status_code == "ERROR").label("has_errors"),
                (func.max(SpanRecord.end_time_unix_nano) - func.min(SpanRecord.start_time_unix_nano)).label("trace_duration")
            )
            .where(*where_clauses)
            .group_by(SpanRecord.trace_id)
            .order_by(desc("start_time"), desc(SpanRecord.trace_id))
            .limit(limit + 1)
        )

        if cursor:
            try:
                decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
                c_time_str, c_tid = decoded.split(":")
                c_time = int(c_time_str)
                agg_stmt = agg_stmt.having(
                    or_(
                        func.min(SpanRecord.start_time_unix_nano) < c_time,
                        and_(
                            func.min(SpanRecord.start_time_unix_nano) == c_time,
                            SpanRecord.trace_id < c_tid
                        )
                    )
                )
            except Exception:
                pass

        rows = (await session.execute(agg_stmt)).all()
        has_more = len(rows) > limit
        if has_more:
            effective_rows = rows[:limit]
            last_item = effective_rows[-1]
            next_cursor = base64.urlsafe_b64encode(f"{last_item.start_time}:{last_item.trace_id}".encode()).decode()
        else:
            effective_rows = rows
            next_cursor = None

        results: List[TraceSearchResult] = []
        for row in effective_rows:
            trace_id = row.trace_id
            start_time = row.start_time
            end_time = row.end_time
            span_count = row.span_count
            has_errors = bool(row.has_errors)
            duration = max(0, end_time - start_time)

            root_stmt = (
                select(SpanRecord.name, SpanRecord.service_name)
                .where(SpanRecord.tenant_id == tenant_id, SpanRecord.trace_id == trace_id)
                .order_by(case((SpanRecord.parent_span_id.is_(None), 0), else_=1), SpanRecord.start_time_unix_nano.asc())
                .limit(1)
            )
            root_row = (await session.execute(root_stmt)).first()
            root_name = root_row[0] if root_row else "unknown"
            root_service = root_row[1] if root_row else "unknown"

            results.append(
                TraceSearchResult(
                    trace_id=trace_id,
                    root_name=root_name,
                    root_service=root_service,
                    start_time_unix_nano=start_time,
                    duration_nanos=duration,
                    span_count=span_count,
                    has_errors=has_errors
                )
            )

        return results, next_cursor

    async def aggregate_traces(
        self,
        session: AsyncSession,
        tenant_id: str,
        service_name: Optional[str] = None,
        min_time_ns: Optional[int] = None,
        max_time_ns: Optional[int] = None,
    ) -> TraceAggregationResult:
        where_clauses = [SpanRecord.tenant_id == tenant_id]
        if service_name:
            subq = select(SpanRecord.trace_id).where(
                SpanRecord.tenant_id == tenant_id,
                SpanRecord.service_name == service_name
            ).distinct()
            where_clauses.append(SpanRecord.trace_id.in_(subq))
        if min_time_ns is not None:
            where_clauses.append(SpanRecord.start_time_unix_nano >= min_time_ns)
        if max_time_ns is not None:
            where_clauses.append(SpanRecord.start_time_unix_nano <= max_time_ns)

        per_trace_subq = (
            select(
                SpanRecord.trace_id,
                func.count().label("span_count"),
                func.bool_or(SpanRecord.status_code == "ERROR").label("has_error"),
                (func.max(SpanRecord.end_time_unix_nano) - func.min(SpanRecord.start_time_unix_nano)).label("duration")
            )
            .where(*where_clauses)
            .group_by(SpanRecord.trace_id)
            .subquery()
        )

        overall_stmt = select(
            func.count().label("total_traces"),
            func.count().filter(per_trace_subq.c.has_error.is_(True)).label("error_traces"),
            func.sum(per_trace_subq.c.span_count).label("total_spans"),
            func.avg(per_trace_subq.c.duration).label("avg_duration"),
            func.min(per_trace_subq.c.duration).label("min_duration"),
            func.max(per_trace_subq.c.duration).label("max_duration"),
        ).select_from(per_trace_subq)

        row = (await session.execute(overall_stmt)).first()
        if not row or not row.total_traces:
            return TraceAggregationResult(
                total_traces=0,
                error_traces=0,
                error_rate=0.0,
                avg_duration_nanos=0.0,
                min_duration_nanos=0,
                max_duration_nanos=0,
                total_spans=0,
                avg_spans_per_trace=0.0
            )

        total_traces = int(row.total_traces)
        error_traces = int(row.error_traces or 0)
        total_spans = int(row.total_spans or 0)
        error_rate = float(error_traces) / float(total_traces) if total_traces > 0 else 0.0
        avg_spans = float(total_spans) / float(total_traces) if total_traces > 0 else 0.0
        avg_duration = float(row.avg_duration or 0.0)
        min_duration = int(row.min_duration or 0)
        max_duration = int(row.max_duration or 0)

        return TraceAggregationResult(
            total_traces=total_traces,
            error_traces=error_traces,
            error_rate=error_rate,
            avg_duration_nanos=avg_duration,
            min_duration_nanos=min_duration,
            max_duration_nanos=max_duration,
            total_spans=total_spans,
            avg_spans_per_trace=avg_spans
        )
