import { useSettings } from '../context/SettingsContext';
import { X } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose }) {
    const { settings, updateSettings } = useSettings();

    if (!isOpen) return null;

    const handleUnitChange = (e) => {
        const newUnit = e.target.value;
        const currentUnit = settings.unitPreference;
        
        if (newUnit !== currentUnit) {
            const multiplier = newUnit === 'large' ? 0.001 : 1000;
            
            updateSettings({ 
                unitPreference: newUnit,
                thresholds: {
                    energy_draw: Number((settings.thresholds.energy_draw * multiplier).toFixed(3)),
                    carbon_emissions: Number((settings.thresholds.carbon_emissions * multiplier).toFixed(3))
                }
            });
        }
    };

    const handleThresholdChange = (metric, value) => {
        updateSettings({
            thresholds: {
                ...settings.thresholds,
                [metric]: Number(value)
            }
        });
    };

    return (
        <div className="settings-modal-overlay" onClick={onClose}>
            <div className="settings-modal-content" onClick={e => e.stopPropagation()}>
                <div className="settings-modal-header">
                    <h2>Dashboard Settings</h2>
                    <button className="close-btn" onClick={onClose}><X size={24} /></button>
                </div>

                <div className="settings-section">
                    <h3>Unit Preference</h3>
                    <p className="settings-desc">Choose the scale for displaying energy and emission values.</p>
                    <div className="radio-group">
                        <label>
                            <input
                                type="radio"
                                name="unit"
                                value="standard"
                                checked={settings.unitPreference === 'standard'}
                                onChange={handleUnitChange}
                            />
                            Standard (kWh, kgCO₂)
                        </label>
                        <label>
                            <input
                                type="radio"
                                name="unit"
                                value="large"
                                checked={settings.unitPreference === 'large'}
                                onChange={handleUnitChange}
                            />
                            Large (MWh, Tonnes CO₂)
                        </label>
                    </div>
                </div>

                <div className="settings-section">
                    <h3>Alert Thresholds</h3>
                    <p className="settings-desc">Set the critical limits for the UI glow indicators.</p>
                    
                    <div className="input-group">
                        <label>Energy Draw ({settings.unitPreference === 'large' ? 'MWh' : 'kWh'})</label>
                        <input
                            type="number"
                            value={settings.thresholds.energy_draw}
                            onChange={(e) => handleThresholdChange('energy_draw', e.target.value)}
                        />
                    </div>
                    
                    <div className="input-group">
                        <label>Carbon Emissions ({settings.unitPreference === 'large' ? 'Tonnes CO₂' : 'kgCO₂'})</label>
                        <input
                            type="number"
                            value={settings.thresholds.carbon_emissions}
                            onChange={(e) => handleThresholdChange('carbon_emissions', e.target.value)}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
