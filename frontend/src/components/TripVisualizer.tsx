import { motion } from "motion/react";
import { Trip, TrailerConfig } from "../types";

interface Props {
  trip: Trip;
  trailer: TrailerConfig;
}

export default function TripVisualizer({ trip, trailer }: Props) {
  const scale = 0.05;
  const padding = 20;
  const viewWidth = (trailer.lowerLength + trailer.upperLength) * scale + padding * 2;
  const viewHeight = 320;
  const crossSectionHeight = 200;
  const deckHeight = 34;

  const colors: Record<string, string> = {
    "ПШЛ-1": "#ef4444",
    "ЛМ": "#f59e0b",
    "ПТ": "#3b82f6",
    "ПП": "#10b981",
    "ПБ": "#8b5cf6",
  };

  return (
    <div className="bg-white p-3 rounded-xl shadow-inner w-full overflow-hidden">
      <svg
        viewBox={`0 0 ${viewWidth} ${viewHeight}`}
        width="100%"
        height="auto"
        className="block w-full border-b-4 border-slate-800 bg-slate-50/50 rounded-t-lg"
        preserveAspectRatio="xMidYMid meet"
      >
        <line x1={0} y1={viewHeight - 20} x2={viewWidth} y2={viewHeight - 20} stroke="#94a3b8" strokeWidth={2} />

        <rect
          x={padding}
          y={viewHeight - 20 - deckHeight}
          width={trailer.lowerLength * scale}
          height={deckHeight}
          fill="#334155"
        />
        <rect
          x={padding + trailer.lowerLength * scale}
          y={viewHeight - 20 - deckHeight - trailer.heightDiff * scale}
          width={trailer.upperLength * scale}
          height={deckHeight + trailer.heightDiff * scale}
          fill="#475569"
        />

        <line
          x1={padding + trailer.idealCGFromRear * scale}
          y1={42}
          x2={padding + trailer.idealCGFromRear * scale}
          y2={viewHeight - 10}
          stroke="#ef4444"
          strokeDasharray="5,5"
          strokeWidth={1}
        />
        <text x={padding + trailer.idealCGFromRear * scale} y={34} fontSize={10} fill="#ef4444" textAnchor="middle">
          Ось ЦТ
        </text>

        {trip.items.map((placed, i) => {
          const x = padding + placed.x * scale;
          const isUpper = placed.x >= trailer.lowerLength;
          const baseY = isUpper
            ? viewHeight - 20 - deckHeight - trailer.heightDiff * scale
            : viewHeight - 20 - deckHeight;
          const y = baseY - (placed.z + placed.height) * scale;

          return (
            <motion.g key={i} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}>
              <rect
                x={x}
                y={y}
                width={placed.length * scale}
                height={placed.height * scale}
                fill={colors[placed.item.code] || "#94a3b8"}
                stroke="white"
                strokeWidth={0.5}
              />
              <text x={x + 2} y={y + 10} fontSize={8} fill="white" className="pointer-events-none">
                {placed.item.code}
              </text>
            </motion.g>
          );
        })}

        <circle cx={padding + trip.cgXFromRear * scale} cy={viewHeight - 34} r={6} fill="#fbbf24" stroke="black" />
      </svg>

      <div className="mt-4 w-full">
        <svg
          viewBox={`0 0 ${viewWidth} ${crossSectionHeight}`}
          width="100%"
          height="auto"
          className="block w-full bg-slate-50 border border-slate-200 rounded-lg"
          preserveAspectRatio="xMidYMid meet"
        >
          <rect
            x={padding}
            y={40}
            width={(trailer.lowerLength + trailer.upperLength) * scale}
            height={trailer.totalWidth * scale}
            fill="#f1f5f9"
            stroke="#94a3b8"
          />

          <line
            x1={padding}
            y1={40 + (trailer.totalWidth * scale) / 2}
            x2={padding + (trailer.lowerLength + trailer.upperLength) * scale}
            y2={40 + (trailer.totalWidth * scale) / 2}
            stroke="#ef4444"
            strokeDasharray="4,4"
            strokeWidth={1}
            opacity={0.5}
          />
          <line
            x1={padding + trailer.idealCGFromRear * scale}
            y1={40}
            x2={padding + trailer.idealCGFromRear * scale}
            y2={40 + trailer.totalWidth * scale}
            stroke="#ef4444"
            strokeDasharray="4,4"
            strokeWidth={1}
            opacity={0.5}
          />

          <text x={padding + trailer.idealCGFromRear * scale} y={35} fontSize={8} fill="#ef4444" textAnchor="middle">
            Ось X (ЦТ)
          </text>
          <text x={padding - 5} y={40 + (trailer.totalWidth * scale) / 2} fontSize={8} fill="#ef4444" textAnchor="end" dominantBaseline="middle">
            Ось Y
          </text>

          {trip.items.map((placed, i) => (
            <motion.rect
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.8 }}
              x={padding + placed.x * scale}
              y={40 + placed.y * scale}
              width={placed.length * scale}
              height={placed.width * scale}
              fill={colors[placed.item.code] || "#94a3b8"}
              stroke="#f8fafc"
              strokeWidth={1}
            />
          ))}

          <circle
            cx={padding + trip.cgXFromRear * scale}
            cy={40 + (trailer.totalWidth * scale) / 2}
            r={8}
            fill="none"
            stroke="#ef4444"
            strokeWidth={2}
          />
          <circle
            cx={padding + trip.cgXFromRear * scale}
            cy={40 + (trailer.totalWidth * scale) / 2}
            r={2}
            fill="#ef4444"
          />
        </svg>
      </div>
    </div>
  );
}
