import { AlertTriangle, XCircle } from 'lucide-react';
import { useState } from 'react';

/**
 * AlertPanel — renders active alerts in two modes:
 *   mode="header"  → inline card(s) for the top navigation bar (full detail)
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

    const formatTime = (ts) =>
        new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric' }) +
        ' · ' +
        new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    /* ── Inline header cards — full detail, horizontal layout ── */
    if (mode === 'header') {
        return (
            <div className="header-alert-panel">
                {visibleAlerts.map((alert) => (
                    <div
                        key={alert.alert_id}
                        className={`header-alert-card ${alert.severity === 'CRITICAL' ? 'critical' : 'warning'}`}
                    >
                        <AlertTriangle size={15} className="header-alert-icon" />
                        <div className="header-alert-body">
                            <span className="header-alert-type">
                                {alert.type.replace(/_/g, ' ')}
                            </span>
                            <span className="header-alert-message">{alert.message}</span>
                            <span className="header-alert-time">{formatTime(alert.timestamp)}</span>
                        </div>
                        <button
                            className="header-alert-close"
                            onClick={() => handleDismiss(alert.alert_id)}
                            aria-label="Dismiss alert"
                        >
                            <XCircle size={14} />
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
