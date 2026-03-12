import { useState } from 'react';
import { Download, Loader2, Activity, BarChart2, TrendingUp, Bell } from 'lucide-react';
import { useSettings } from '../context/SettingsContext';

const RANGE_OPTIONS = [
    { value: '24H', label: '24H' },
    { value: '7D',  label: '7 Days' },
    { value: 'MTD', label: 'MTD' },
];

const REPORT_CARDS = [
    {
        type: 'timeseries',
        icon: Activity,
        title: 'Timeseries Report',
        description: 'Hourly energy draw and carbon emissions — both recorded actuals and ML-predicted values — for the selected time window.',
        hasRange: true,
        defaultRange: '24H',
    },
    {
        type: 'summary',
        icon: BarChart2,
        title: 'Daily Summary',
        description: 'Aggregated daily statistics: total, peak, and average hourly energy draw and carbon emissions per calendar day.',
        hasRange: true,
        defaultRange: '7D',
    },
    {
        type: 'forecast',
        icon: TrendingUp,
        title: '24H Forecast',
        description: 'The next 24 hours of ML-predicted energy draw and carbon emissions, anchored to the most recent actual readings.',
        hasRange: false,
        defaultRange: null,
    },
    {
        type: 'alerts',
        icon: Bell,
        title: 'Alert History',
        description: 'Every hourly reading where energy draw or carbon emissions exceeded your configured thresholds, within the selected window.',
        hasRange: true,
        defaultRange: '7D',
    },
];

function ReportCard({ card, energyThreshold, carbonThreshold }) {
    const [selectedRange, setSelectedRange] = useState(card.defaultRange);
    const [isGenerating, setIsGenerating] = useState(false);
    const Icon = card.icon;

    const handleDownload = async () => {
        try {
            setIsGenerating(true);
            const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

            let url = `${baseUrl}/api/v1/metrics/report?type=${card.type}`;
            if (card.hasRange) url += `&range=${selectedRange}`;
            if (card.type === 'alerts') {
                url += `&energy_threshold=${energyThreshold}&carbon_threshold=${carbonThreshold}`;
            }

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to generate report');

            const blob = await response.blob();
            const objectUrl = window.URL.createObjectURL(blob);

            // Derive filename from Content-Disposition if present, else build one
            const disposition = response.headers.get('Content-Disposition') || '';
            const match = disposition.match(/filename=(.+)/);
            const now = new Date();
            const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
            const filename = match ? match[1] : `EcoShift_${card.type}_${dateStr}.csv`;

            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = objectUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(objectUrl);
            document.body.removeChild(a);
        } catch (err) {
            console.error('Report download error:', err);
            alert('Failed to generate report. Please try again.');
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="report-card glass-panel">
            <div className="report-card-header">
                <div className="report-card-icon">
                    <Icon size={20} />
                </div>
                <h3 className="report-card-title">{card.title}</h3>
            </div>

            <p className="report-card-description">{card.description}</p>

            <div className="report-card-footer">
                {card.hasRange && (
                    <div className="report-range-selector">
                        {RANGE_OPTIONS.map(opt => (
                            <button
                                key={opt.value}
                                className={`range-btn ${selectedRange === opt.value ? 'active' : ''}`}
                                onClick={() => setSelectedRange(opt.value)}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                )}

                <button
                    className="action-btn report-download-btn"
                    onClick={handleDownload}
                    disabled={isGenerating}
                >
                    {isGenerating ? (
                        <>
                            <Loader2 className="spinner-small" size={15} />
                            Generating…
                        </>
                    ) : (
                        <>
                            <Download size={15} />
                            Download CSV
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}

export default function Reports() {
    const { settings } = useSettings();
    const energyThreshold = settings.thresholds.energy_draw;
    const carbonThreshold = settings.thresholds.carbon_emissions;

    return (
        <div className="reports-container">
            <div className="reports-page-header">
                <h2 className="reports-page-title">Data Exports</h2>
                <p className="reports-page-subtitle">Download CSV reports — choose a type and time window.</p>
            </div>

            <div className="reports-grid">
                {REPORT_CARDS.map(card => (
                    <ReportCard
                        key={card.type}
                        card={card}
                        energyThreshold={energyThreshold}
                        carbonThreshold={carbonThreshold}
                    />
                ))}
            </div>
        </div>
    );
}
