import { useSettings } from '../context/SettingsContext';
export default function Controls({ timeRange, setTimeRange, metric, setMetric }) {
    const { settings } = useSettings();
    const isLarge = settings.unitPreference === 'large';

    return (
        <div className="controls-container">
            <div className="control-group">
                <span className="control-label">Time Range</span>
                <div className="segmented-control">
                    <button
                        className={timeRange === '24H' ? 'active' : ''}
                        onClick={() => setTimeRange('24H')}
                    >
                        24H
                    </button>
                    <button
                        className={timeRange === '7D' ? 'active' : ''}
                        onClick={() => setTimeRange('7D')}
                    >
                        7 Days
                    </button>
                    <button
                        className={timeRange === 'MTD' ? 'active' : ''}
                        onClick={() => setTimeRange('MTD')}
                    >
                        MTD
                    </button>
                </div>
            </div>

            <div className="control-group">
                <span className="control-label">Metric</span>
                <div className="segmented-control">
                    <button
                        className={metric === 'energy_draw' ? 'active' : ''}
                        onClick={() => setMetric('energy_draw')}
                    >
                        Energy Draw {isLarge ? '(MWh)' : '(kWh)'}
                    </button>
                    <button
                        className={metric === 'carbon_emissions' ? 'active' : ''}
                        onClick={() => setMetric('carbon_emissions')}
                    >
                        Carbon Emissions {isLarge ? '(Tonnes)' : '(kgCO2)'}
                    </button>
                </div>
            </div>
        </div>
    );
}
