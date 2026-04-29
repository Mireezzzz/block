import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Truck, Calculator, Package, AlertCircle, Weight, ArrowRight, Table, Loader2 } from "lucide-react";
import { INITIAL_ITEMS, DEFAULT_TRAILER } from "./constants";
import { JBIItem, TrailerConfig, Trip } from "./types";
import TripVisualizer from "./components/TripVisualizer";

const API_URL = import.meta.env.VITE_API_URL ?? "";

export default function App() {
  const [items, setItems] = useState<JBIItem[]>(INITIAL_ITEMS);
  const [trailer, setTrailer] = useState<TrailerConfig>(DEFAULT_TRAILER);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [isCalculated, setIsCalculated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalWeight = useMemo(() => items.reduce((sum, item) => sum + item.weight * item.count, 0), [items]);
  const totalItems = useMemo(() => items.reduce((sum, item) => sum + item.count, 0), [items]);

  const handleCalculate = async () => {
    setIsCalculated(false);
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items, trailer }),
      });
      if (!res.ok) throw new Error(`Ошибка сервера: ${res.status}`);
      const data = await res.json();
      setTrips(data.trips);
      setIsCalculated(true);
    } catch (e: any) {
      setError(e.message ?? "Не удалось связаться с сервером");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setItems(INITIAL_ITEMS.map(it => ({ ...it })));
    setTrips([]);
    setIsCalculated(false);
    setError(null);
  };

  const updateItemCount = (id: string, count: number) => {
    setItems(items.map(it => it.id === id ? { ...it, count: Math.max(0, count) } : it));
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans p-4 md:p-8">
      <header className="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Truck className="text-blue-600" /> JBI Load Optimizer
          </h1>
          <p className="text-slate-500 mt-1">Оптимизация загрузки железобетонных изделий на полуприцеп</p>
        </div>

        <div className="flex bg-white p-4 rounded-xl shadow-sm border border-slate-200 divide-x divide-slate-100">
          <div className="px-4">
            <p className="text-xs font-semibold text-slate-400 uppercase">Общий вес</p>
            <p className="text-lg font-bold">{(totalWeight / 1000).toFixed(1)} т</p>
          </div>
          <div className="px-4">
            <p className="text-xs font-semibold text-slate-400 uppercase">Изделий</p>
            <p className="text-lg font-bold">{totalItems} шт</p>
          </div>
          <div className="px-4">
            <p className="text-xs font-semibold text-slate-400 uppercase">Лимит прицепа</p>
            <p className="text-lg font-bold text-blue-600">{(trailer.maxWeight / 1000).toFixed(1)} т</p>
          </div>
          <div className="px-4 border-l border-slate-100">
            <p className="text-xs font-semibold text-slate-400 uppercase">Будет рейсов</p>
            <p className="text-lg font-bold text-indigo-600 italic">
              {isCalculated ? trips.length : '—'}
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Inputs */}
        <section className="lg:col-span-4 space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="p-4 bg-slate-900 text-white flex items-center gap-2">
              <Table size={18} />
              <h2 className="font-semibold">Номенклатура груза</h2>
            </div>
            <div className="p-4 space-y-4">
              {items.map((item) => (
                <div key={item.id} className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-100 hover:border-blue-200 transition-colors">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{item.code}</span>
                      <h3 className="text-sm font-medium">{item.name}</h3>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      {item.length}×{item.width}×{item.height} мм • {item.weight} кг
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => updateItemCount(item.id, item.count - 1)}
                      className="w-8 h-8 rounded-full flex items-center justify-center bg-white border border-slate-200 hover:bg-slate-50"
                    >-</button>
                    <input
                      type="number"
                      value={item.count}
                      onChange={(e) => updateItemCount(item.id, parseInt(e.target.value) || 0)}
                      className="w-12 text-center text-sm font-bold bg-transparent border-none focus:ring-0"
                    />
                    <button
                      onClick={() => updateItemCount(item.id, item.count + 1)}
                      className="w-8 h-8 rounded-full flex items-center justify-center bg-white border border-slate-200 hover:bg-slate-50"
                    >+</button>
                  </div>
                </div>
              ))}

              {error && (
                <div className="flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg p-3 text-sm">
                  <AlertCircle size={16} />
                  {error}
                </div>
              )}

              <div className="flex gap-2 mt-4">
                <button
                  onClick={handleCalculate}
                  disabled={isLoading}
                  className="flex-1 py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold rounded-xl transition-all shadow-lg shadow-blue-200 flex items-center justify-center gap-2"
                >
                  {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Calculator size={20} />}
                  {isLoading ? "Считаю..." : "Рассчитать"}
                </button>
                <button
                  onClick={handleReset}
                  className="px-4 py-4 bg-slate-100 hover:bg-slate-200 text-slate-600 font-bold rounded-xl transition-all flex items-center justify-center"
                  title="Сбросить"
                >
                  Сброс
                </button>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <AlertCircle size={18} className="text-amber-500" /> Параметры прицепа
            </h3>
            <div className="grid grid-cols-2 gap-4 text-sm text-slate-600">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1 uppercase">Грузоподъемность</label>
                <input
                  type="number"
                  value={trailer.maxWeight}
                  onChange={(e) => setTrailer({ ...trailer, maxWeight: parseInt(e.target.value) })}
                  className="w-full p-2 bg-slate-50 rounded border border-slate-200 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1 uppercase">Ширина площадки</label>
                <input
                  type="number"
                  value={trailer.totalWidth}
                  className="w-full p-2 bg-slate-100 rounded border border-slate-200 font-mono cursor-not-allowed"
                  disabled
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1 uppercase">Ось ЦТ (от зада)</label>
                <div className="relative">
                  <input
                    type="number"
                    value={trailer.idealCGFromRear}
                    disabled
                    className="w-full p-2 bg-slate-100 rounded border border-slate-200 font-mono cursor-not-allowed"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">мм</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Right Column: Results */}
        <section className="lg:col-span-8 space-y-8">
          {!isCalculated ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-300 py-20 bg-white/50 rounded-3xl border-2 border-dashed border-slate-200">
              <Package size={48} className="mb-4 opacity-50" />
              <p className="text-xl font-medium">Настройте груз и нажмите «Рассчитать»</p>
            </div>
          ) : (
            <AnimatePresence>
              <div className="space-y-8">
                {trips.map((trip, idx) => (
                  <motion.div
                    key={trip.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className="bg-white rounded-3xl shadow-md border border-slate-200 overflow-hidden"
                  >
                    <div className="p-6 border-b border-slate-100 grid grid-cols-1 md:grid-cols-12 gap-6">
                      <div className="md:col-span-3 flex items-center gap-4">
                        <div className="w-12 h-12 bg-slate-900 text-white rounded-2xl flex items-center justify-center text-xl font-bold shrink-0">
                          {trip.id}
                        </div>
                        <div>
                          <h3 className="font-bold text-lg leading-none italic">Рейс №{trip.id}</h3>
                          <p className="text-slate-400 text-[10px] uppercase font-bold mt-1 tracking-wider">План загрузки</p>
                        </div>
                      </div>

                      <div className="md:col-span-6 flex items-center">
                        <div className="grid grid-cols-2 gap-x-6 gap-y-1 w-full">
                          {Object.entries(
                            trip.items.reduce((acc, pi) => {
                              acc[pi.item.name] = (acc[pi.item.name] || 0) + (pi.item.count || 1);
                              return acc;
                            }, {} as Record<string, number>)
                          ).map(([name, count]) => (
                            <div key={name} className="flex justify-between items-center text-sm">
                              <span className="text-slate-500 truncate mr-2 italic">{name}</span>
                              <span className="font-black text-slate-800">{count} шт.</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="md:col-span-3 flex flex-col justify-center border-l border-slate-50 pl-6 gap-3">
                        <div>
                          <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase mb-1">
                            <span>Масса</span>
                            <span className={trip.totalWeight > trailer.maxWeight ? 'text-red-500' : 'text-blue-600'}>
                              {(trip.totalWeight / 1000).toFixed(1)} т
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${trip.totalWeight > trailer.maxWeight ? 'bg-red-500' : 'bg-blue-600'}`}
                              style={{ width: `${Math.min(100, (trip.totalWeight / trailer.maxWeight) * 100)}%` }}
                            />
                          </div>
                        </div>
                        <div>
                          <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Центровка</p>
                          <div className={`text-sm font-black flex items-center gap-1 ${Math.abs(trip.cgMismatch) > 500 ? 'text-amber-600' : 'text-green-600'}`}>
                            {Math.abs(trip.cgMismatch) < 100 ? 'ИДЕАЛЬНО' : `ЦТ: ${trip.cgXFromRear.toFixed(0)} мм`}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="p-8 bg-white">
                      <TripVisualizer trip={trip} trailer={trailer} />
                    </div>
                  </motion.div>
                ))}
              </div>
            </AnimatePresence>
          )}
        </section>
      </main>

      <footer className="max-w-7xl mx-auto mt-20 pt-8 border-t border-slate-200 pb-12 text-center text-slate-400 text-sm">
        <p>© 2026 JBI Load Optimizer Pro. Все расчеты являются ориентировочными.</p>
      </footer>
    </div>
  );
}