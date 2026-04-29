import { JBIItem, TrailerConfig } from "./types";

export const DEFAULT_TRAILER: TrailerConfig = {
  maxWeight: 24000,
  totalWidth: 2400,
  lowerLength: 11180,
  lowerMaxHeight: 2950,
  upperLength: 3500,
  upperMaxHeight: 2600,
  heightDiff: 350,
  idealCGFromRear: 7340,
};

export const INITIAL_ITEMS: JBIItem[] = [
  { id: "1", code: "ПШЛ-1", name: "Шахта лифта", width: 2830, length: 2030, height: 2988, weight: 8065, count: 2 },
  { id: "2", code: "ЛМ", name: "Лестница", width: 1050, length: 4200, height: 220, weight: 2420, count: 4 },
  { id: "3", code: "ПТ", name: "Плита перекрытия", width: 2400, length: 6940, height: 160, weight: 6779, count: 10 },
  { id: "4", code: "ПП", name: "Плита пустотная", width: 1200, length: 6320, height: 120, weight: 2256, count: 20 },
  { id: "5", code: "ПБ", name: "Плита балкона", width: 1200, length: 3810, height: 210, weight: 2207, count: 5 },
];
