export interface SpanItem {
  trace_id: string;
  span_id: string;
  parent_span_id?: string | null;
  service_name: string;
  name: string;
  kind: string;
  start_time_unix_nano: number;
  end_time_unix_nano: number;
  duration_nanos: number;
  status_code: string;
  status_message?: string | null;
  attributes: Record<string, any>;
  events: Array<Record<string, any>>;
  links: Array<Record<string, any>>;
}

export interface TraceSummary {
  trace_id: string;
  root_service_name: string;
  root_name: string;
  start_time_unix_nano: number;
  end_time_unix_nano: number;
  duration_nanos: number;
  span_count: number;
  error_count: number;
}

export interface SearchTracesParams {
  service?: string;
  operation?: string;
  min_duration_ms?: number;
  max_duration_ms?: number;
  status?: string;
  start_time_ns?: number;
  end_time_ns?: number;
  limit?: number;
  cursor?: string;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

export interface SearchTracesResponse {
  traces: TraceSummary[];
  next_cursor?: string | null;
  total_matches?: number;
}

export interface TraceDetailResponse {
  trace_id: string;
  spans: SpanItem[];
  duration_nanos: number;
  span_count: number;
  error_count: number;
  root_service: string;
}

export class TracingApiClient {
  private baseUrl: string;
  private tenantId: string;

  constructor(
    baseUrl: string = typeof window !== 'undefined' && window.location.hostname.includes('github.io')
      ? 'https://aj-tracing-backend.onrender.com/api/v1'
      : '/api/v1',
    tenantId: string = 'default-tenant'
  ) {
    this.baseUrl = baseUrl;
    this.tenantId = tenantId;
  }

  setTenantId(tenantId: string) {
    this.tenantId = tenantId;
  }

  private get headers(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      'X-Tenant-ID': this.tenantId
    };
  }

  async searchTraces(params: SearchTracesParams = {}): Promise<SearchTracesResponse> {
    const query = new URLSearchParams();
    if (params.service) query.set('service', params.service);
    if (params.operation) query.set('operation', params.operation);
    if (params.min_duration_ms) query.set('min_duration_ms', params.min_duration_ms.toString());
    if (params.max_duration_ms) query.set('max_duration_ms', params.max_duration_ms.toString());
    if (params.status) query.set('status', params.status);
    if (params.limit) query.set('limit', params.limit.toString());
    if (params.cursor) query.set('cursor', params.cursor);
    if (params.sort_by) query.set('sort_by', params.sort_by);
    if (params.sort_dir) query.set('sort_dir', params.sort_dir);

    const res = await fetch(`${this.baseUrl}/traces/search?${query.toString()}`, {
      headers: this.headers
    });
    if (!res.ok) {
      throw new Error(`Failed to search traces: ${res.statusText}`);
    }
    return res.json();
  }

  async getTrace(traceId: string): Promise<TraceDetailResponse> {
    const res = await fetch(`${this.baseUrl}/traces/${traceId}`, {
      headers: this.headers
    });
    if (!res.ok) {
      if (res.status === 404) throw new Error('Trace not found');
      throw new Error(`Failed to fetch trace: ${res.statusText}`);
    }
    return res.json();
  }

  async listServices(): Promise<string[]> {
    const res = await fetch(`${this.baseUrl}/services`, {
      headers: this.headers
    });
    if (!res.ok) throw new Error('Failed to fetch services');
    const data = await res.json();
    return data.services || [];
  }

  async getOperations(service: string): Promise<string[]> {
    const res = await fetch(`${this.baseUrl}/services/${encodeURIComponent(service)}/operations`, {
      headers: this.headers
    });
    if (!res.ok) throw new Error('Failed to fetch operations');
    const data = await res.json();
    return data.operations || [];
  }

  async getDependencies(): Promise<Array<{ caller: string; callee: string; call_count: number }>> {
    const res = await fetch(`${this.baseUrl}/dependencies`, {
      headers: this.headers
    });
    if (!res.ok) throw new Error('Failed to fetch dependencies');
    const data = await res.json();
    return data.dependencies || [];
  }

  async getCriticalPath(traceId: string): Promise<{ critical_path_span_ids: string[]; critical_path_duration_nanos: number }> {
    const res = await fetch(`${this.baseUrl}/traces/${encodeURIComponent(traceId)}/critical-path`, {
      headers: this.headers
    });
    if (!res.ok) throw new Error('Failed to fetch critical path');
    return await res.json();
  }
}

export const apiClient = new TracingApiClient();
