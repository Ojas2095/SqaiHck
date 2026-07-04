import { useState, useEffect } from 'react'
import {
  Mic, MicOff, Globe, FileText, CheckCircle2, AlertCircle,
  User, Calendar, Stethoscope, Pill, Activity, Heart,
  Languages, Volume2, RefreshCw, Save, Send, Clock
} from 'lucide-react'
import './EHRCreator.css'

const languages = [
  { code: 'hi', name: 'हिन्दी', label: 'Hindi' },
  { code: 'en', name: 'English', label: 'English' },
  { code: 'ta', name: 'தமிழ்', label: 'Tamil' },
  { code: 'te', name: 'తెలుగు', label: 'Telugu' },
  { code: 'bn', name: 'বাংলা', label: 'Bengali' },
  { code: 'mr', name: 'मराठी', label: 'Marathi' },
  { code: 'gu', name: 'ગુજરાતી', label: 'Gujarati' },
  { code: 'kn', name: 'ಕನ್ನಡ', label: 'Kannada' },
]

const sampleTranscription = [
  { text: 'रोगी का नाम ', entity: null },
  { text: 'रमेश कुमार', entity: 'PERSON' },
  { text: ', उम्र ', entity: null },
  { text: '45 वर्ष', entity: 'AGE' },
  { text: '। मुख्य शिकायत — ', entity: null },
  { text: 'सिरदर्द', entity: 'SYMPTOM' },
  { text: ' और ', entity: null },
  { text: 'जोड़ों में दर्द', entity: 'SYMPTOM' },
  { text: ' पिछले ', entity: null },
  { text: '2 सप्ताह', entity: 'DURATION' },
  { text: ' से। ', entity: null },
  { text: 'प्रकृति — वात-पित्त', entity: 'PRAKRITI' },
  { text: '। पिछली दवाई — ', entity: null },
  { text: 'अश्वगंधा', entity: 'MEDICINE' },
  { text: ' और ', entity: null },
  { text: 'त्रिफला', entity: 'MEDICINE' },
  { text: '।', entity: null },
]

const entityColors = {
  PERSON: { bg: 'rgba(59, 130, 246, 0.15)', color: '#60A5FA', label: 'Patient Name' },
  AGE: { bg: 'rgba(244, 196, 48, 0.15)', color: '#FFD760', label: 'Age' },
  SYMPTOM: { bg: 'rgba(239, 68, 68, 0.15)', color: '#EF4444', label: 'Symptom' },
  DURATION: { bg: 'rgba(233, 30, 140, 0.15)', color: '#FF4DAF', label: 'Duration' },
  PRAKRITI: { bg: 'rgba(255, 107, 53, 0.15)', color: '#FF8A5C', label: 'Prakriti' },
  MEDICINE: { bg: 'rgba(74, 157, 110, 0.15)', color: '#6BBF8D', label: 'Medicine' },
}

const ehrFields = {
  patientName: 'Ramesh Kumar',
  age: '45',
  gender: 'Male',
  prakriti: 'Vata-Pitta',
  chiefComplaint: 'Headache, Joint Pain',
  duration: '2 weeks',
  symptoms: ['Headache (Shirahshool)', 'Joint Pain (Sandhivata)', 'Mild Fatigue'],
  vitals: { bp: '130/85', pulse: '78 bpm', temp: '98.4°F', weight: '72 kg' },
  previousMeds: ['Ashwagandha', 'Triphala'],
  diagnosis: 'Sandhivata (Osteoarthritis) with Shirahshool',
}

export default function EHRCreator() {
  const [isRecording, setIsRecording] = useState(false)
  const [selectedLang, setSelectedLang] = useState('hi')
  const [showTranscription, setShowTranscription] = useState(true)
  const [waveAmplitudes, setWaveAmplitudes] = useState(Array(20).fill(8))

  // Simulate wave animation when recording
  useEffect(() => {
    if (!isRecording) return
    const interval = setInterval(() => {
      setWaveAmplitudes(prev => prev.map(() => 8 + Math.random() * 24))
    }, 150)
    return () => clearInterval(interval)
  }, [isRecording])

  return (
    <div className="ehr-page animate-fade-in">
      <div className="page-header">
        <h1>Voice EHR Creator</h1>
        <p>Create Electronic Health Records using multilingual voice input with AI-powered NER</p>
      </div>

      <div className="ehr-layout">
        {/* Left Panel — Voice Input */}
        <div className="ehr-voice-panel">
          {/* Language Selector */}
          <div className="glass-card no-hover mb-20">
            <div className="section-header">
              <div className="flex items-center gap-8">
                <Languages size={18} className="text-saffron" />
                <span className="section-title">Input Language</span>
              </div>
            </div>
            <div className="lang-grid">
              {languages.map((lang) => (
                <button
                  key={lang.code}
                  className={`lang-btn ${selectedLang === lang.code ? 'active' : ''}`}
                  onClick={() => setSelectedLang(lang.code)}
                >
                  <span className="lang-native">{lang.name}</span>
                  <span className="lang-label">{lang.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Voice Recorder */}
          <div className="glass-card no-hover voice-recorder-card">
            <div className="recorder-area">
              {/* Wave Visualization */}
              <div className="wave-container">
                {waveAmplitudes.map((amp, i) => (
                  <div
                    key={i}
                    className={`wave-bar ${isRecording ? 'active' : ''}`}
                    style={{
                      height: isRecording ? `${amp}px` : '8px',
                      animationDelay: `${i * 0.05}s`
                    }}
                  />
                ))}
              </div>

              {/* Mic Button */}
              <button
                className={`mic-button ${isRecording ? 'recording' : ''}`}
                onClick={() => {
                  setIsRecording(!isRecording)
                  if (!isRecording) setShowTranscription(true)
                }}
              >
                {isRecording ? <MicOff size={28} /> : <Mic size={28} />}
              </button>

              <p className="recorder-status">
                {isRecording ? (
                  <><span className="pulse-dot critical" style={{ display: 'inline-block', marginRight: 8 }} /> Recording in हिन्दी...</>
                ) : (
                  'Tap the microphone to start recording'
                )}
              </p>

              {isRecording && (
                <div className="recording-timer">
                  <Clock size={14} />
                  <span>00:34</span>
                </div>
              )}
            </div>
          </div>

          {/* Transcription Panel */}
          {showTranscription && (
            <div className="glass-card no-hover mt-20">
              <div className="section-header">
                <div className="flex items-center gap-8">
                  <FileText size={18} className="text-saffron" />
                  <span className="section-title">Live Transcription</span>
                </div>
                <div className="badge badge-saffron">NER Active</div>
              </div>

              <div className="transcription-text">
                {sampleTranscription.map((segment, i) => (
                  segment.entity ? (
                    <span
                      key={i}
                      className="ner-highlight"
                      style={{
                        background: entityColors[segment.entity].bg,
                        color: entityColors[segment.entity].color,
                      }}
                      title={entityColors[segment.entity].label}
                    >
                      {segment.text}
                    </span>
                  ) : (
                    <span key={i}>{segment.text}</span>
                  )
                ))}
              </div>

              {/* Entity Legend */}
              <div className="entity-legend">
                {Object.entries(entityColors).map(([key, val]) => (
                  <span key={key} className="entity-tag" style={{ background: val.bg, color: val.color }}>
                    {val.label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Panel — Structured EHR */}
        <div className="ehr-form-panel">
          <div className="glass-card no-hover">
            <div className="section-header">
              <div className="flex items-center gap-8">
                <Stethoscope size={18} className="text-sage" />
                <span className="section-title">Structured Health Record</span>
              </div>
              <div className="flex gap-8">
                <div className="badge badge-sage">Auto-Populated</div>
                <div className="badge badge-sky">AYUSH Grid</div>
              </div>
            </div>

            {/* Patient Info */}
            <div className="ehr-section">
              <h4 className="ehr-section-title">
                <User size={16} />
                Patient Information
              </h4>
              <div className="ehr-fields-grid">
                <div className="ehr-field">
                  <label>Full Name</label>
                  <div className="ehr-field-value">{ehrFields.patientName}</div>
                </div>
                <div className="ehr-field">
                  <label>Age</label>
                  <div className="ehr-field-value">{ehrFields.age} years</div>
                </div>
                <div className="ehr-field">
                  <label>Gender</label>
                  <div className="ehr-field-value">{ehrFields.gender}</div>
                </div>
                <div className="ehr-field">
                  <label>Prakriti Type</label>
                  <div className="ehr-field-value highlight">{ehrFields.prakriti}</div>
                </div>
              </div>
            </div>

            <div className="divider" />

            {/* Clinical Data */}
            <div className="ehr-section">
              <h4 className="ehr-section-title">
                <Activity size={16} />
                Clinical Assessment
              </h4>
              <div className="ehr-field full-width">
                <label>Chief Complaint</label>
                <div className="ehr-field-value">{ehrFields.chiefComplaint}</div>
              </div>
              <div className="ehr-field full-width">
                <label>Duration</label>
                <div className="ehr-field-value">{ehrFields.duration}</div>
              </div>
              <div className="ehr-field full-width">
                <label>Symptoms</label>
                <div className="ehr-symptoms">
                  {ehrFields.symptoms.map((s, i) => (
                    <span key={i} className="symptom-tag">{s}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="divider" />

            {/* Vitals */}
            <div className="ehr-section">
              <h4 className="ehr-section-title">
                <Heart size={16} />
                Vitals
              </h4>
              <div className="vitals-grid">
                {Object.entries(ehrFields.vitals).map(([key, val]) => (
                  <div key={key} className="vital-item">
                    <span className="vital-label">{key.toUpperCase()}</span>
                    <span className="vital-value">{val}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="divider" />

            {/* Medications & Diagnosis */}
            <div className="ehr-section">
              <h4 className="ehr-section-title">
                <Pill size={16} />
                Previous Medications
              </h4>
              <div className="ehr-symptoms">
                {ehrFields.previousMeds.map((m, i) => (
                  <span key={i} className="symptom-tag sage">{m}</span>
                ))}
              </div>
            </div>

            <div className="divider" />

            <div className="ehr-section">
              <h4 className="ehr-section-title">
                <CheckCircle2 size={16} />
                AI-Generated Diagnosis
              </h4>
              <div className="diagnosis-box">
                <span className="diagnosis-text">{ehrFields.diagnosis}</span>
                <span className="diagnosis-confidence">Confidence: 89%</span>
              </div>
            </div>

            {/* Actions */}
            <div className="ehr-actions">
              <button className="btn btn-secondary">
                <RefreshCw size={16} />
                Re-process
              </button>
              <button className="btn btn-secondary">
                <Save size={16} />
                Save Draft
              </button>
              <button className="btn btn-primary">
                <Send size={16} />
                Submit to AHMIS
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
