import { motion } from "motion/react";
import { Trip, TrailerConfig } from "../types";

interface Props {
  trip: Trip;
  trailer: TrailerConfig;
}

export default function TripVisualizer({ trip, trailer }: Props) {
  // Scale factor: trailer is ~14.6m, screen is ~800px.
  const scale = 0.05; 
  const viewWidth = (trailer.lowerLength + trailer.upperLength) * scale + 100;
  const viewHeight = 400;

  // Colors for different items
  const colors: Record<string, string> = {
    "ПШЛ-1": "#ef4444", // red
    "ЛМ": "#f59e0b", // amber
    "ПТ": "#3b82f6", // blue
    "ПП": "#10b981", // emerald
    "ПБ": "#8b5cf6", // violet
  };

  return (
    <div className="bg-white p-4 rounded-xl shadow-inner overflow-x-auto">
      <div className="min-w-[800px]">
        <svg width={viewWidth} height={viewHeight} className="border-b-4 border-slate-800 bg-slate-50/50 rounded-t-lg">
          {/* Ground */}
          <line x1={0} y1={viewHeight - 20} x2={viewWidth} y2={viewHeight - 20} stroke="#94a3b8" strokeWidth={2} />
          
          {/* Trailer Bed */}
          {/* Lower deck */}
          <rect 
            x={20} 
            y={viewHeight - 20 - 40} 
            width={trailer.lowerLength * scale} 
            height={40} 
            fill="#334155" 
          />
          {/* Upper deck (Gusak) */}
          <rect 
            x={20 + trailer.lowerLength * scale} 
            y={viewHeight - 20 - 40 - trailer.heightDiff * scale} 
            width={trailer.upperLength * scale} 
            height={40 + trailer.heightDiff * scale} 
            fill="#475569" 
          />

          {/* Ideal CG Axis */}
          <line 
            x1={20 + trailer.idealCGFromRear * scale} 
            y1={50} 
            x2={20 + trailer.idealCGFromRear * scale} 
            y2={viewHeight - 10} 
            stroke="#ef4444" 
            strokeDasharray="5,5" 
            strokeWidth={1}
          />
          <text x={20 + trailer.idealCGFromRear * scale} y={40} fontSize={10} fill="#ef4444" textAnchor="middle">Ось ЦТ</text>

          {/* Items */}
          {trip.items.map((placed, i) => {
            const x = 20 + placed.x * scale;
            // z=0 is at bed height.
            // If x is on lower deck: y = bed_y - (z + height) * scale
            // If x is on upper deck: y = bed_y_upper - (z + height) * scale
            const isUpper = placed.x >= trailer.lowerLength;
            const baseY = isUpper 
                ? (viewHeight - 20 - 40 - trailer.heightDiff * scale)
                : (viewHeight - 20 - 40);
                
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
                <text 
                  x={x + 2} 
                  y={y + 10} 
                  fontSize={8} 
                  fill="white" 
                  className="pointer-events-none"
                >
                  {placed.item.code}
                </text>
              </motion.g>
            );
          })}

          {/* Calculated CG */}
          <circle 
            cx={20 + trip.cgXFromRear * scale} 
            cy={viewHeight - 40} 
            r={6} 
            fill="#fbbf24" 
            stroke="black"
          />
        </svg>

        <div className="mt-4">
            <svg width={viewWidth} height={200} className="bg-slate-50 border border-slate-200 rounded-lg">
                {/* Trailer boundary */}
                <rect 
                  x={20} 
                  y={40} 
                  width={(trailer.lowerLength + trailer.upperLength) * scale} 
                  height={trailer.totalWidth * scale} 
                  fill="#f1f5f9" 
                  stroke="#94a3b8" 
                />

                {/* CG Guide Lines (X and Y) */}
                <line 
                  x1={20} 
                  y1={40 + (trailer.totalWidth * scale / 2)} 
                  x2={20 + (trailer.lowerLength + trailer.upperLength) * scale} 
                  y2={40 + (trailer.totalWidth * scale / 2)} 
                  stroke="#ef4444" 
                  strokeDasharray="4,4" 
                  strokeWidth={1} 
                  opacity={0.5}
                />
                <line 
                  x1={20 + trailer.idealCGFromRear * scale} 
                  y1={40} 
                  x2={20 + trailer.idealCGFromRear * scale} 
                  y2={40 + (trailer.totalWidth * scale)} 
                  stroke="#ef4444" 
                  strokeDasharray="4,4" 
                  strokeWidth={1} 
                  opacity={0.5}
                />
                
                {/* Axes Labels */}
                <text x={20 + trailer.idealCGFromRear * scale} y={35} fontSize={8} fill="#ef4444" textAnchor="middle">Ось X (ЦТ)</text>
                <text x={15} y={40 + (trailer.totalWidth * scale / 2)} fontSize={8} fill="#ef4444" textAnchor="end" dominantBaseline="middle">Ось Y</text>
                
                {trip.items.map((placed, i) => (
                    <motion.rect 
                        key={i}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 0.8 }}
                        x={20 + placed.x * scale}
                        y={40 + placed.y * scale}
                        width={placed.length * scale}
                        height={placed.width * scale}
                        fill={colors[placed.item.code] || "#94a3b8"}
                        stroke="#f8fafc"
                        strokeWidth={1}
                    />
                ))}

                {/* Actual CG Indicator */}
                <circle 
                  cx={20 + trip.cgXFromRear * scale} 
                  cy={40 + (trailer.totalWidth * scale / 2)} 
                  r={8} 
                  fill="none" 
                  stroke="#ef4444" 
                  strokeWidth={2}
                />
                <circle 
                  cx={20 + trip.cgXFromRear * scale} 
                  cy={40 + (trailer.totalWidth * scale / 2)} 
                  r={2} 
                  fill="#ef4444" 
                />
            </svg>
        </div>
      </div>
    </div>
  );
}
