import { Suspense } from 'react';

// You will set NEXT_PUBLIC_API_URL in Vercel to point to your Render backend URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export const revalidate = 60; // Revalidate data every 60 seconds

type IndexData = {
  origin: string;
  destination: string;
  base_period: string;
  index_value: number;
  n_observations: number;
  computed_at_utc: string;
};

async function getIndexData(): Promise<IndexData[]> {
  try {
    const res = await fetch(`${API_URL}/index/latest`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) {
      throw new Error('Failed to fetch data');
    }
    return res.json();
  } catch (error) {
    console.error(error);
    return [];
  }
}

export default async function Dashboard() {
  const data = await getIndexData();

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-indigo-500/30">
      {/* Background Gradients */}
      <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-600/20 blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-blue-600/20 blur-[120px]"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <header className="mb-12">
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-blue-400 to-sky-400">
            Airfare Price Index
          </h1>
          <p className="mt-4 text-lg text-slate-400 max-w-2xl">
            Real-time tracking of airline pricing dynamics across major Indian domestic routes.
          </p>
        </header>

        <section className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-2xl">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-white">Latest Route Indices</h2>
            <span className="inline-flex items-center rounded-full bg-indigo-400/10 px-3 py-1 text-sm font-medium text-indigo-400 ring-1 ring-inset ring-indigo-400/30">
              Live Data
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-sm font-medium text-slate-400">
                  <th className="pb-3 px-4">Route (Origin &rarr; Dest)</th>
                  <th className="pb-3 px-4">Base Period</th>
                  <th className="pb-3 px-4">Index Value</th>
                  <th className="pb-3 px-4">Observations</th>
                  <th className="pb-3 px-4 text-right">Computed At (UTC)</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {data.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-500">
                      No data available or backend is currently asleep.
                    </td>
                  </tr>
                ) : (
                  data.map((row, idx) => {
                    const isElevated = row.index_value > 105;
                    const isLow = row.index_value < 95;
                    return (
                      <tr 
                        key={`${row.origin}-${row.destination}`} 
                        className="border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors"
                      >
                        <td className="py-4 px-4 font-medium text-slate-200">
                          {row.origin} <span className="text-slate-500 mx-1">&rarr;</span> {row.destination}
                        </td>
                        <td className="py-4 px-4 text-slate-400">{row.base_period}</td>
                        <td className="py-4 px-4">
                          <span className={`inline-flex font-mono font-medium ${
                            isElevated ? 'text-rose-400' : isLow ? 'text-emerald-400' : 'text-slate-200'
                          }`}>
                            {row.index_value.toFixed(2)}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-slate-400">{row.n_observations}</td>
                        <td className="py-4 px-4 text-right text-slate-500">
                          {new Date(row.computed_at_utc).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
