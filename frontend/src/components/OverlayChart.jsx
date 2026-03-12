import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    ReferenceLine
} from 'recharts';
import { useSettings } from '../context/SettingsContext';

function prepareChartData(timeseries, metricType, unitPreference) {
    if (!timeseries) return [];

    const divisor = unitPreference === 'large' ? 1000 : 1;

    return timeseries.map(item => {
        const dt = new Date(item.timestamp);
        
        // Clean short X-axis label: if it's midnight, show the date, otherwise show just the time
        const isMidnight = dt.getHours() === 0 && dt.getMinutes() === 0;
        const xAxisLabel = isMidnight 
            ? dt.toLocaleDateString([], { month: 'short', day: 'numeric' })
            : dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Full explicit timestamp for the hover tooltip context
        const fullDate = dt.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' + dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        return {
            timestamp: fullDate, // Used as the unique key and for the tooltip header internally if we didn't customize
            xAxisLabel: xAxisLabel,
            fullDate: fullDate,
            actual: item[metricType]?.actual ? item[metricType].actual / divisor : null,
            predicted: item[metricType]?.predicted ? item[metricType].predicted / divisor : null,
            _hoverTracker: (item[metricType]?.actual || item[metricType]?.predicted || 0) / divisor,
        };
    });
}

const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        return (
            <div style={{ backgroundColor: 'rgba(11, 15, 25, 0.9)', border: '1px solid #2c3445', borderRadius: '8px', padding: '10px' }}>
                <p style={{ color: '#e6edf3', margin: '0 0 5px 0', fontWeight: 'bold' }}>{payload[0].payload.fullDate}</p>
                {payload.map((entry, index) => {
                    if (entry.dataKey === '_hoverTracker') return null;
                    return (
                        <p key={`item-${index}`} style={{ color: entry.color, margin: 0 }}>
                            {entry.name}: {entry.value != null ? entry.value.toFixed(2) : 'N/A'}
                        </p>
                    );
                })}
            </div>
        );
    }
    return null;
};

export default function OverlayChart({ data, metric }) {
    const { settings } = useSettings();
    const chartData = prepareChartData(data, metric, settings.unitPreference);

    const divisor = settings.unitPreference === 'large' ? 1000 : 1;
    const alertThreshold = settings.thresholds[metric] / divisor;

    // Choose colors based on the selected metric
    const actualColor = metric === 'energy_draw' ? '#00e1ff' : '#00ff88';
    const predictedColor = metric === 'energy_draw' ? '#6f7db1' : '#6bb489';

    const renderCustomActiveDot = (props, color, dataKey) => {
        const { cx, cy, payload } = props;
        if (payload && payload[dataKey] == null) {
            return null;
        }
        return <circle cx={cx} cy={cy} r={6} fill={color} strokeWidth={0} />;
    };

    return (
        <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart
                    data={chartData}
                    margin={{
                        top: 20,
                        right: 30,
                        left: 20,
                        bottom: 10,
                    }}
                >
                    <CartesianGrid strokeDasharray="3 3" stroke="#2c3445" vertical={false} />
                    <XAxis
                        dataKey="timestamp"
                        tickFormatter={(value) => {
                            const point = chartData.find(d => d.timestamp === value);
                            return point ? point.xAxisLabel : value;
                        }}
                        stroke="#8b949e"
                        tick={{ fill: '#8b949e' }}
                        tickMargin={10}
                        axisLine={false}
                    />
                    <YAxis
                        stroke="#8b949e"
                        tick={{ fill: '#8b949e' }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />

                    {/* Threshold Line */}
                    <ReferenceLine 
                        y={alertThreshold} 
                        label={{ position: 'top', value: 'Threshold', fill: '#ff3366', fontSize: 12 }} 
                        stroke="#ff3366" 
                        strokeDasharray="3 3" 
                        strokeWidth={2}
                    />

                    {/* Actual line (solid) */}
                    <Line
                        type="monotone"
                        dataKey="actual"
                        stroke={actualColor}
                        strokeWidth={3}
                        dot={{ r: 4, fill: actualColor, strokeWidth: 0 }}
                        activeDot={(props) => renderCustomActiveDot(props, actualColor, 'actual')}
                        name="Actual"
                        connectNulls={false}
                        isAnimationActive={true}
                    />

                    {/* Predicted line (dashed) overlaying the same axis */}
                    <Line
                        type="monotone"
                        dataKey="predicted"
                        stroke={predictedColor}
                        strokeWidth={3}
                        strokeDasharray="5 5"
                        dot={false}
                        activeDot={(props) => renderCustomActiveDot(props, predictedColor, 'predicted')}
                        name="Predicted"
                        connectNulls={true}
                        isAnimationActive={true}
                    />

                    {/* Invisible tracker line to ensure hover Voronoi nodes exist across entire chart */}
                    <Line
                        type="monotone"
                        dataKey="_hoverTracker"
                        stroke="transparent"
                        dot={false}
                        activeDot={false}
                        isAnimationActive={false}
                        name="_hoverTracker"
                        legendType="none"
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
