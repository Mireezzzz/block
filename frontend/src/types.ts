export interface JBIItem {
  id: string;
  code: string;
  name: string;
  width: number;
  length: number;
  height: number;
  weight: number;
  count: number;
}

export interface TrailerConfig {
  maxWeight: number;
  totalWidth: number;
  lowerLength: number;
  lowerMaxHeight: number;
  upperLength: number;
  upperMaxHeight: number;
  heightDiff: number;
  idealCGFromRear: number;
}

export interface PlacedItem {
  item: JBIItem;
  x: number; // from rear
  y: number; // width offset
  z: number; // height offset
  width: number;
  length: number;
  height: number;
}

export interface Trip {
  id: number;
  items: PlacedItem[];
  totalWeight: number;
  cgXFromRear: number;
  cgMismatch: number;
}
