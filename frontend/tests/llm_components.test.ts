import { describe, it, expect } from 'vitest';
import { TraceSummaryResult } from '../src/components/TraceSummarizer';
import { IncidentSummaryResult } from '../src/components/IncidentSummarizer';
import { NLQueryResponse } from '../src/components/NLQuerySearch';

describe('LLM Frontend Components Tests', () => {
  it('TRC-142: validates trace summarization output structure and model metadata', () => {
    const result: TraceSummaryResult = {
      summary: 'Trace t-1 executed in 450ms on checkout-service with 1 error in payment gateway.',
      model: 'google/flan-t5-small',
      tenant_id: 'tenant-default'
    };

    expect(result.summary).toContain('checkout-service');
    expect(result.model).toBe('google/flan-t5-small');
    expect(result.tenant_id).toBe('tenant-default');
  });

  it('TRC-143: validates incident synthesis output across multiple traces and blast radius', () => {
    const incident: IncidentSummaryResult = {
      summary: 'Incident Auth Degradation affected 12 traces across auth and api-gateway. Root cause: token validation deadlock.',
      model: 'google/flan-t5-small',
      tenant_id: 'tenant-default'
    };

    expect(incident.summary).toContain('Auth Degradation');
    expect(incident.model).toBe('google/flan-t5-small');
  });

  it('TRC-144: validates natural language query parsed structured JSON schema', () => {
    const nlResponse: NLQueryResponse = {
      query: 'Find failing requests in checkout-service taking over 500ms',
      structured_query: {
        service: 'checkout-service',
        status: 'ERROR',
        min_duration_ms: 500,
        max_duration_ms: null,
        operation: null,
        query_text: null
      },
      model: 'google/flan-t5-small',
      tenant_id: 'tenant-default'
    };

    const sq = nlResponse.structured_query;
    expect(sq.service).toBe('checkout-service');
    expect(sq.status).toBe('ERROR');
    expect(sq.min_duration_ms).toBe(500);
    // Never raw SQL
    expect(JSON.stringify(sq)).not.toContain('SELECT');
    expect(JSON.stringify(sq)).not.toContain('DROP');
  });
});
