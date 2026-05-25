import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { formatFCFACompact, formatFCFA } from "../../utils/format";

const COLORS = ["#0A2540", "#FF6200", "#C62828", "#2E7D32", "#7C5BC4"];

function ChartCard({ title, subtitle, children, testId, height = 260 }) {
  return (
    <div
      data-testid={testId}
      className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-5 shadow-sm"
    >
      <div className="mb-4">
        <h3 className="text-sm font-bold text-[#0A2540] dark:text-white tracking-tight">
          {title}
        </h3>
        {subtitle && (
          <p className="text-[11px] text-gray-500 dark:text-white/50 mt-0.5">{subtitle}</p>
        )}
      </div>
      <div style={{ width: "100%", height }}>{children}</div>
    </div>
  );
}

const tooltipStyle = {
  backgroundColor: "#0A2540",
  border: "none",
  borderRadius: 8,
  color: "white",
  fontSize: 12,
  padding: "8px 12px",
};

export function VentesLineChart({ data }) {
  return (
    <ChartCard
      title="Évolution du chiffre d'affaires"
      subtitle="Sur les 12 derniers mois (FCFA)"
      testId="chart-ventes-12mois"
    >
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 5, right: 16, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-white/10" />
          <XAxis dataKey="mois" tick={{ fontSize: 11, fill: "#6b7280" }} />
          <YAxis tickFormatter={formatFCFACompact} tick={{ fontSize: 11, fill: "#6b7280" }} />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(v) => formatFCFA(v)}
            labelStyle={{ color: "#FF6200", fontWeight: 600 }}
          />
          <Line
            type="monotone"
            dataKey="ca"
            stroke="#FF6200"
            strokeWidth={2.5}
            dot={{ fill: "#FF6200", r: 4 }}
            activeDot={{ r: 6, fill: "#0A2540" }}
            name="CA"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function VentesCategorieBarChart({ data }) {
  return (
    <ChartCard
      title="Ventes par catégorie produit"
      subtitle="Cumul année scolaire 2026-2027"
      testId="chart-ventes-categorie"
    >
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 5, right: 16, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="categorie" tick={{ fontSize: 10, fill: "#6b7280" }} interval={0} />
          <YAxis tickFormatter={formatFCFACompact} tick={{ fontSize: 11, fill: "#6b7280" }} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => formatFCFA(v)} />
          <Bar dataKey="ca" fill="#0A2540" radius={[6, 6, 0, 0]} name="CA" />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function PaiementsPieChart({ data }) {
  return (
    <ChartCard
      title="Répartition des paiements"
      subtitle="Par mode de règlement"
      testId="chart-paiements-mode"
    >
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="mode"
            cx="50%"
            cy="50%"
            outerRadius={85}
            innerRadius={45}
            paddingAngle={3}
            label={({ mode, percent }) => `${mode} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
            style={{ fontSize: 11 }}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color || COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => formatFCFA(v)} />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function TopClientsBarChart({ data }) {
  return (
    <ChartCard
      title="Top 5 clients"
      subtitle="Classement par chiffre d'affaires"
      testId="chart-top-clients"
    >
      <ResponsiveContainer>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 16, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
          <XAxis type="number" tickFormatter={formatFCFACompact} tick={{ fontSize: 11, fill: "#6b7280" }} />
          <YAxis
            type="category"
            dataKey="nom"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            width={140}
          />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => formatFCFA(v)} />
          <Bar dataKey="ca" fill="#FF6200" radius={[0, 6, 6, 0]} name="CA" />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
