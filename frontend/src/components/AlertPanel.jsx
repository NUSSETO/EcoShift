import { AlertTriangle, XCircle } from 'lucide-react';
import { useState } from 'react';

/**
 * AlertPanel — renders active alerts in two modes:
 *   mode="header"  → compact horizontal chips for the top navigation bar
 *   mode="default" → full stacked cards (original layout, kept for fallback)
 */
export default function AlertPanel({ alerts, mode = 'default' }) {
    const [dismissedAlerts, setDismissedAlerts] = useState(new Set());

    if (!alerts || alerts.length === 0) return null;

    const visibleAlerts = alerts.filter(alert => !dismissedAlerts.has(alert.alert_id));

    if (visibleAlerts.length === 0) return null;

    const handleDismiss = (alertId) => {
        setDismissedAlerts(prev => new Set(prev).add(alertId));
    };

    /* ── Compact header chips ── */
    if (mode === 'header') {
        return (
            <div className="header-alert-panel">
                {visibleAlerts.map((alert) => (
                    <div
                        key={alert.alert_id}
                        className={`header-alert-chip ${alert.severity === 'CRITICAL' ? 'critical' : 'warning'}`}
                        title={alert.message}
                    >
                        <AlertTriangle size={13} />
                        <span className="header-alert-label">
                            {alert.type.replace(/_/g, ' ')}
                        </span>
                        <button
                            className="header-alert-close"
                            onClick={() => handleDismiss(alert.alert_id)}
                            aria-label="Dismiss alert"
                        >
                            <XCircle size={13} />
                        </button>
                    </div>
                ))}
            </div>
        );
    }

    /* ── Full stacked cards (default) ── */
    return (
        <div className="alert-panel">
            {visibleAlerts.map((alert) => (
                <div
                    key={alert.alert_id}
                    className={`alert-toast ${alert.severity === 'CRITICAL' ? 'critical' : 'warning'}`}
                >
                    <div className="alert-icon">
                        <AlertTriangle size={24} />
                    </div>
                    <div className="alert-content">
                        <h4>{alert.type.replace(/_/g, ' ')}</h4>
                        <p>{alert.message}</p>
                        <span className="alert-time">
                            {new Date(alert.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) + ' ' +
                             new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    </div>
                    <button className="alert-close" onClick={() => handleDismiss(alert.alert_id)}>
                        <XCircle size={20} />
                    </button>
                </div>
            ))}
        </div>
    );
}
