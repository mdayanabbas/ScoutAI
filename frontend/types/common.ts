export type ErrorBody = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export type ErrorResponse = {
  error: ErrorBody;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
};

export type MessageResponse = {
  message: string;
};
