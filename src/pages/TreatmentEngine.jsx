import { useState } from 'react'
import {
  User, Sparkles, Leaf, Apple, PersonStanding, Heart,
  ThumbsUp, ThumbsDown, ChevronRight, BookOpen, Clock,
  Pill, Activity, Brain, Shield, FileText, Star,
  Droplets, Wind, Flame, Mountain
} from 'lucide-react'
import ConfidenceGauge from '../components/ConfidenceGauge'
import './TreatmentEngine.css'

const patientProfile = {
  name: 'Priya Sharma',
  age: 38,
  gender: 'Female',
  prakriti: 'Kapha-Pitta',
  bmi: 29.4,
  conditions: ['Obesity', 'Hypertension (Stage 1)', 'Insulin Resistance'],
  allergies: ['Shellfish'],
  duration: '18 months',
}

const recommendations = [
  {
    category: 'Herbal Medicine',
    icon: Leaf,
    color: 'sage',
    confidence: 92,
    items: [
      { name: 'Guggulu (Commiphora mukul)', dosage: '500mg twice daily', duration: '3 months', evidence: 'Proven lipid-lowering & anti-obesity properties', strength: 'Strong' },
      { name: 'Triphala Churna', dosage: '5g at bedtime with warm water', duration: '6 months', evidence: 'Digestive regulation, gentle weight management', strength: 'Strong' },
      { name: 'Arjuna Bark Extract', dosage: '250mg thrice daily', duration: '3 months', evidence: 'Cardioprotective, BP regulation in Ayurvedic practice', strength: 'Moderate' },
    ]
  },
  {
    category: 'Dietary Plan',
    icon: Apple,
    color: 'gold',
    confidence: 88,
    items: [
      { name: 'Kapha-Pacifying Diet', dosage: 'Warm, light, dry foods; avoid cold/heavy', duration: 'Ongoing', evidence: 'Based on Prakriti-specific dietary guidelines', strength: 'Strong' },
      { name: 'Intermittent Fasting (16:8)', dosage: 'Eating window: 10 AM – 6 PM', duration: '3 months trial', evidence: 'Improves insulin sensitivity, weight management', strength: 'Moderate' },
      { name: 'Turmeric Golden Milk', dosage: '200ml before bed with 1 tsp haldi', duration: 'Ongoing', evidence: 'Anti-inflammatory, metabolic support', strength: 'Moderate' },
    ]
  },
  {
    category: 'Yoga & Exercise',
    icon: PersonStanding,
    color: 'lotus',
    confidence: 95,
    items: [
      { name: 'Surya Namaskar', dosage: '12 rounds, morning', duration: 'Daily', evidence: 'Full-body workout, cardiovascular benefits', strength: 'Strong' },
      { name: 'Pranayama — Kapalbhati', dosage: '100 strokes × 3 sets', duration: 'Daily', evidence: 'Metabolic activation, abdominal fat reduction', strength: 'Strong' },
      { name: 'Ardha Matsyendrasana', dosage: 'Hold 30 sec each side', duration: 'Daily', evidence: 'Stimulates digestive fire (Agni), spinal health', strength: 'Moderate' },
    ]
  },
  {
    category: 'Lifestyle Modifications',
    icon: Heart,
    color: 'sky',
    confidence: 85,
    items: [
      { name: 'Early Rising (Brahma Muhurta)', dosage: 'Wake by 5:30 AM', duration: 'Ongoing', evidence: 'Aligns with circadian rhythm, Kapha balance', strength: 'Moderate' },
      { name: 'Abhyanga (Self-massage)', dosage: 'Warm sesame oil, 15 min before bath', duration: '3× per week', evidence: 'Improves circulation, reduces stress hormones', strength: 'Moderate' },
      { name: 'Digital Detox after 9 PM', dosage: 'No screens 1hr before sleep', duration: 'Ongoing', evidence: 'Improves sleep quality, reduces cortisol', strength: 'Moderate' },
    ]
  },
]

const similarOutcomes = [
  { age: 35, gender: 'F', prakriti: 'Kapha', condition: 'Obesity + HTN', outcome: 'BMI reduced by 4.2, BP normalized', duration: '6 months', success: true },
  { age: 42, gender: 'F', prakriti: 'Kapha-Pitta', condition: 'Obesity + Pre-diabetes', outcome: 'Weight loss 8kg, HbA1c improved', duration: '8 months', success: true },
  { age: 39, gender: 'M', prakriti: 'Kapha', condition: 'Obesity + HTN Stage 1', outcome: 'Partial improvement, needed allopathy add-on', duration: '4 months', success: false },
]

const prakritiInfo = {
  'Kapha-Pitta': {
    dosha: ['Kapha (Primary)', 'Pitta (Secondary)'],
    qualities: ['Heavy', 'Oily', 'Hot', 'Intense'],
    icon: [Droplets, Flame],
    recommendation: 'Focus on lightening, drying, and cooling therapies'
  }
}

export default function TreatmentEngine() {
  const [expandedRec, setExpandedRec] = useState(0)
  const [feedbackGiven, setFeedbackGiven] = useState({})
  
  const [treatmentData, setTreatmentData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  
  const generateTreatmentPlan = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/treatment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ patient_id: 'PAT-1234' })
      });
      const data = await res.json();
      if (res.ok) {
        setTreatmentData(data);
      } else {
        console.error('Failed to generate treatment:', data.detail || data.error);
        alert('Failed to generate: ' + (data.detail || data.error || 'Unknown error'));
      }
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const sendFeedback = async (approved) => {
    if (!treatmentData?.treatment_id) return;
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          treatment_id: treatmentData.treatment_id,
          approved,
          score: approved ? 1.0 : 0.0
        })
      });
      alert(approved ? '✅ Approved — herb weights reinforced' : '❌ Rejected — herb weights penalised');
    } catch (err) {
      console.error('Feedback error:', err);
    }
  };

  return (
    <div className="treatment-page animate-fade-in">
      <div className="page-header">
        <h1>Treatment Recommendation Engine</h1>
        <p>AI-powered personalized AYUSH treatment plans with evidence-based recommendations</p>
      </div>

      <div className="treatment-layout">
        {/* Left — Patient Profile */}
        <div className="treatment-sidebar">
          {/* Patient Card */}
          <div className="glass-card no-hover patient-card">
            <div className="patient-avatar-lg">
              {patientProfile.name.split(' ').map(n => n[0]).join('')}
            </div>
            <h3 className="patient-name">{patientProfile.name}</h3>
            <div className="patient-meta">
              {patientProfile.age} yrs • {patientProfile.gender} • BMI {patientProfile.bmi}
            </div>
            <div style={{ marginTop: '15px' }}>
              <button 
                className="btn btn-primary" 
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={generateTreatmentPlan}
                disabled={isLoading}
              >
                <Sparkles size={16} />
                {isLoading ? 'Generating Plan...' : 'Generate AI Plan (PAT-1234)'}
              </button>
            </div>

            <div className="divider" />

            <div className="patient-detail-section">
              <h5><Sparkles size={14} /> Prakriti Analysis</h5>
              <div className="prakriti-badge">{treatmentData ? treatmentData.prakriti : patientProfile.prakriti}</div>
              <div className="prakriti-doshas">
                <div className="dosha-item">
                  <Droplets size={14} />
                  <span>Kapha</span>
                  <div className="progress-bar"><div className="progress-fill" style={{ width: '75%', background: 'var(--sky)' }} /></div>
                </div>
                <div className="dosha-item">
                  <Flame size={14} />
                  <span>Pitta</span>
                  <div className="progress-bar"><div className="progress-fill" style={{ width: '55%', background: 'var(--saffron)' }} /></div>
                </div>
                <div className="dosha-item">
                  <Wind size={14} />
                  <span>Vata</span>
                  <div className="progress-bar"><div className="progress-fill" style={{ width: '25%', background: 'var(--sage)' }} /></div>
                </div>
              </div>
            </div>

            <div className="divider" />

            <div className="patient-detail-section">
              <h5><Activity size={14} /> Conditions</h5>
              <div className="condition-tags">
                {(treatmentData && treatmentData.symptoms && treatmentData.symptoms.length > 0 ? treatmentData.symptoms : patientProfile.conditions).map((c, i) => (
                  <span key={i} className="condition-tag">{c}</span>
                ))}
              </div>
            </div>

            <div className="divider" />

            <div className="patient-detail-section">
              <h5><Clock size={14} /> Treatment Duration</h5>
              <p className="detail-text">{patientProfile.duration} since first consultation</p>
            </div>
          </div>

          {/* Similar Outcomes */}
          <div className="glass-card no-hover mt-20">
            <div className="section-header">
              <div>
                <div className="section-title">Similar Patient Outcomes</div>
                <div className="section-subtitle">Based on demographic matching</div>
              </div>
            </div>
            <div className="outcomes-list">
              {similarOutcomes.map((o, i) => (
                <div key={i} className="outcome-item">
                  <div className="outcome-header">
                    <span className="outcome-profile">{o.age}{o.gender[0]} • {o.prakriti}</span>
                    <span className={`badge ${o.success ? 'badge-low' : 'badge-medium'}`}>
                      {o.success ? 'Success' : 'Partial'}
                    </span>
                  </div>
                  <p className="outcome-result">{o.outcome}</p>
                  <span className="outcome-duration">{o.duration}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right — Recommendations */}
        <div className="treatment-main">
          <div className="section-header mb-20">
            <div>
              <div className="section-title">AI-Generated Treatment Plan</div>
              <div className="section-subtitle">
                Personalized for {treatmentData ? treatmentData.prakriti : patientProfile.prakriti} constitution
              </div>
            </div>
            <div className="flex gap-8">
              <div className="badge badge-sage">LLM + RAG</div>
              <div className="badge badge-gold">Evidence-Based</div>
            </div>
          </div>
          
          {treatmentData && (
            <div className="glass-card no-hover mb-20" style={{ padding: '20px', borderLeft: '4px solid var(--sage)' }}>
              <h4 style={{ marginBottom: '10px', color: 'var(--sage)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Brain size={18} /> Detailed LLM Recommendation
              </h4>
              <p style={{ whiteSpace: 'pre-wrap', color: '#8a9ba8', fontSize: '14px', lineHeight: '1.6' }}>
                {treatmentData.llm_response || "No detailed reasoning provided."}
              </p>
            </div>
          )}

          {recommendations.map((rec, i) => {
            // If data is fetched, override the first recommendation category
            const currentRec = (treatmentData && i === 0) ? {
              ...rec,
              confidence: Math.round(treatmentData.confidence_score * 100),
              items: [
                { name: treatmentData.herbs, dosage: 'As prescribed', duration: 'Ongoing', evidence: 'RAG DB Evidence', strength: 'Strong' },
                { name: treatmentData.diet, dosage: 'Daily', duration: 'Ongoing', evidence: 'Clinical Guidelines', strength: 'Moderate' },
                { name: treatmentData.yoga, dosage: 'Daily', duration: 'Ongoing', evidence: 'Ayurvedic Principles', strength: 'Moderate' }
              ]
            } : rec;
            
            return (
              <div key={i} className={`recommendation-card ${expandedRec === i ? 'expanded' : ''}`}>
                <div className="rec-header" onClick={() => setExpandedRec(expandedRec === i ? -1 : i)}>
                  <div className="rec-left">
                    <div className={`rec-icon ${currentRec.color}`}>
                      <currentRec.icon size={20} />
                    </div>
                    <div>
                      <h4 className="rec-category">{currentRec.category}</h4>
                      <span className="rec-count">{currentRec.items.length} recommendations</span>
                    </div>
                  </div>
                  <div className="rec-right">
                    <ConfidenceGauge
                      value={currentRec.confidence}
                      size={56}
                      color={currentRec.color === 'sage' ? 'var(--sage)' : currentRec.color === 'gold' ? 'var(--gold)' : currentRec.color === 'lotus' ? 'var(--lotus)' : 'var(--sky)'}
                    />
                    <ChevronRight size={18} className={`rec-chevron ${expandedRec === i ? 'rotated' : ''}`} />
                  </div>
                </div>

                {expandedRec === i && (
                  <div className="rec-content">
                    {currentRec.items.map((item, j) => (
                      <div key={j} className="rec-item">
                        <div className="rec-item-header">
                          <h5 className="rec-item-name">{item.name}</h5>
                          <span className={`evidence-badge ${item.strength.toLowerCase()}`}>
                            <Star size={10} />
                            {item.strength} Evidence
                          </span>
                        </div>
                        <div className="rec-item-details">
                          <div className="rec-detail">
                            <Pill size={13} />
                            <span><strong>Dosage:</strong> {item.dosage}</span>
                          </div>
                          <div className="rec-detail">
                            <Clock size={13} />
                            <span><strong>Duration:</strong> {item.duration}</span>
                          </div>
                          <div className="rec-detail">
                            <BookOpen size={13} />
                            <span><strong>Evidence:</strong> {item.evidence}</span>
                          </div>
                        </div>
                        <div className="rec-feedback">
                          <span className="feedback-label">Rate this recommendation:</span>
                          <button
                            className={`feedback-btn up ${feedbackGiven[`${i}-${j}`] === 'up' ? 'active' : ''}`}
                            onClick={() => setFeedbackGiven({ ...feedbackGiven, [`${i}-${j}`]: 'up' })}
                          >
                            <ThumbsUp size={14} />
                          </button>
                          <button
                            className={`feedback-btn down ${feedbackGiven[`${i}-${j}`] === 'down' ? 'active' : ''}`}
                            onClick={() => setFeedbackGiven({ ...feedbackGiven, [`${i}-${j}`]: 'down' })}
                          >
                            <ThumbsDown size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
