// Shared response-envelope types, mirrored from
// backend/src/tarakdingdung/presentation/http/schemas/response.py. Every module
// under src/lib/api/ reuses these instead of redeclaring them.

export interface PageResponse {
  page: number;
  limit: number;
  total_items: number;
}

export interface PageDataResponse<T> {
  data: T[];
  page: PageResponse;
}

export interface IdResponse {
  id: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
}

/** AuditResponse in response.py — the trailing fields are optional on the wire. */
export interface AuditFields {
  created_at: string;
  updated_at?: string | null;
  deleted_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  deleted_by?: string | null;
}

/** Query params common to every paginated list endpoint. */
export interface PageQuery {
  page?: number;
  limit?: number;
  search?: string;
}
