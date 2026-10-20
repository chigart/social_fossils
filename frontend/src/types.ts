export type Resource<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
};

export type SortDirection = "asc" | "desc";
