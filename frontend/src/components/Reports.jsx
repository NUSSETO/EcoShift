import { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';

export default function Reports() {
    const [isGenerating, setIsGenerating] = useState(false);

    const handleGenerateReport = async () => {
        try {
            setIsGenerating(true);
            const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${baseUrl}/api/v1/metrics/report?format=csv`);
            
            if (!response.ok) throw new Error('Failed to generate report');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            
            // Generate filename based on current timestamp
            const now = new Date();
            const timestamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
            const filename = `EcoShift_Report_${timestamp}.csv`;
            
            // Create a temporary anchor element and trigger download
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error downloading report:', error);
            alert('Failed to generate report. Please try again.');
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="reports-container">
            <section className="context-card glow-card" style={{ marginBottom: '2rem' }}>
                <h2>Data Exports</h2>
                <p>Generate detailed CSV reports comprising historical timeseries data and machine learning feature projections.</p>
            </section>
            
            <div className="glass-panel">
                <div className="control-group" style={{ alignItems: 'flex-start' }}>
                    <span className="control-label" style={{ marginBottom: '1rem' }}>Timeseries Report</span>
                    <button 
                        className="action-btn" 
                        onClick={handleGenerateReport}
                        disabled={isGenerating}
                    >
                        {isGenerating ? (
                            <>
                                <Loader2 className="spinner-small" />
                                Generating...
                            </>
                        ) : (
                            <>
                                <Download size={16} />
                                Generate CSV Report
                            </>
                        )}
                    </button>
                    <p style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Includes energy draw (kWh) and carbon emissions (kgCO2) aligning actual readings with ML-derived predictions.
                    </p>
                </div>
            </div>
        </div>
    );
}
