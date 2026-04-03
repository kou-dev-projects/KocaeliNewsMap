export type FilterState = {
  category: string;
  district: string;
  dateFrom: string;
  dateTo: string;
};

export type NewsQueryFilters = {
  categories?: string[];
  districts?: string[];
  search?: string;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
};
