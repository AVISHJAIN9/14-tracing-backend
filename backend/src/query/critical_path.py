"""
Critical Path Analyzer for Distributed Traces.
Computes the sequence of dependent spans determining the overall trace latency.
"""

from typing import List, Dict, Any

class CriticalPathAnalyzer:
    @staticmethod
    def compute_critical_path(spans: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not spans:
            return {
                "critical_path_span_ids": [],
                "critical_path_duration_nanos": 0,
                "segments": []
            }

        by_id = {s["span_id"]: s for s in spans}
        children: Dict[str, List[Dict[str, Any]]] = {}
        roots = []

        for s in spans:
            pid = s.get("parent_span_id")
            if not pid or pid not in by_id:
                roots.append(s)
            else:
                children.setdefault(pid, []).append(s)

        for pid in children:
            children[pid].sort(key=lambda x: x["start_time_unix_nano"])

        if not roots:
            roots = [min(spans, key=lambda x: x["start_time_unix_nano"])]

        memo: Dict[str, tuple[int, List[str]]] = {}

        def get_critical_path_from(span: Dict[str, Any]) -> tuple[int, List[str]]:
            sid = span["span_id"]
            if sid in memo:
                return memo[sid]

            c_list = children.get(sid, [])
            if not c_list:
                res = (span["duration_nanos"], [sid])
                memo[sid] = res
                return res

            best_child_dur = -1
            best_child_path: List[str] = []
            for c in c_list:
                c_dur, c_path = get_critical_path_from(c)
                if c_dur > best_child_dur:
                    best_child_dur = c_dur
                    best_child_path = c_path

            res = (span["duration_nanos"], [sid] + best_child_path)
            memo[sid] = res
            return res

        best_dur = -1
        best_path: List[str] = []
        for r in roots:
            r_dur, r_path = get_critical_path_from(r)
            if r_dur > best_dur:
                best_dur = r_dur
                best_path = r_path

        segments = [by_id[sid] for sid in best_path if sid in by_id]
        return {
            "critical_path_span_ids": best_path,
            "critical_path_duration_nanos": max(0, best_dur),
            "segments": [
                {
                    "span_id": s["span_id"],
                    "service_name": s["service_name"],
                    "name": s["name"],
                    "start_time_unix_nano": s["start_time_unix_nano"],
                    "end_time_unix_nano": s["end_time_unix_nano"],
                    "duration_nanos": s["duration_nanos"]
                }
                for s in segments
            ]
        }
