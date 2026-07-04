import { useState, useRef, useEffect } from 'react'
import { Globe, Mic, MicOff, ArrowRight, ArrowLeft, CheckCircle2, User, Activity, Send, Sparkles } from 'lucide-react'
import './PatientOnboarding.css'

const LANGUAGES = [
  { code: 'en', name: 'English', native: 'English', speechCode: 'en-IN' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी', speechCode: 'hi-IN' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்', speechCode: 'ta-IN' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు', speechCode: 'te-IN' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা', speechCode: 'bn-IN' },
  { code: 'mr', name: 'Marathi', native: 'मराठी', speechCode: 'mr-IN' },
  { code: 'gu', name: 'Gujarati', native: 'ગુજરાતી', speechCode: 'gu-IN' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ', speechCode: 'kn-IN' },
]

export default function PatientOnboarding() {
  const [step, setStep] = useState(1)
  const totalSteps = 4
  const [formData, setFormData] = useState({
    language: '',
    languageSpeechCode: 'en-IN',
    name: '',
    age: '',
    gender: '',
    symptoms: ''
  })
  const [isRecording, setIsRecording] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const recognitionRef = useRef(null)
  const textareaRef = useRef(null)

  // Real Web Speech API setup
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = formData.languageSpeechCode
      
      recognition.onresult = (event) => {
        let finalTranscript = ''
        let interimTranscript = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const t = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += t + ' '
          } else {
            interimTranscript = t
          }
        }
        if (finalTranscript) {
          setFormData(prev => ({
            ...prev,
            symptoms: prev.symptoms + finalTranscript
          }))
        }
      }

      recognition.onerror = () => {
        setIsRecording(false)
      }

      recognition.onend = () => {
        setIsRecording(false)
      }

      recognitionRef.current = recognition
    }
  }, [formData.languageSpeechCode])

  const handleNext = () => {
    if (step < totalSteps) setStep(s => s + 1)
  }

  const handleBack = () => {
    if (step > 1) setStep(s => s - 1)
  }

  const handleSelectLanguage = (lang) => {
    setFormData(prev => ({
      ...prev,
      language: lang.name,
      languageSpeechCode: lang.speechCode
    }))
  }

  const toggleRecording = () => {
    const recognition = recognitionRef.current
    if (!recognition) {
      // Fallback for browsers without speech API
      setIsRecording(true)
      setTimeout(() => {
        setFormData(prev => ({
          ...prev,
          symptoms: prev.symptoms + (prev.symptoms ? ' ' : '') + 'I have a mild headache and feel a bit feverish since morning.'
        }))
        setIsRecording(false)
      }, 3000)
      return
    }

    if (isRecording) {
      recognition.stop()
      setIsRecording(false)
    } else {
      recognition.lang = formData.languageSpeechCode
      recognition.start()
      setIsRecording(true)
    }
  }

  const handleSubmit = () => {
    setSubmitted(true)
  }

  const handleStartOver = () => {
    setStep(1)
    setSubmitted(false)
    setFormData({ language: '', languageSpeechCode: 'en-IN', name: '', age: '', gender: '', symptoms: '' })
  }

  const progressPercent = (step / totalSteps) * 100

  // Success screen
  if (submitted) {
    return (
      <div className="onboarding-container">
        <div className="success-card animate-scale-in">
          <div className="success-icon-wrapper">
            <CheckCircle2 size={48} />
          </div>
          <h2>Thank You, {formData.name}!</h2>
          <p className="success-message">
            Your information has been submitted successfully. A healthcare practitioner will review your symptoms and get back to you shortly.
          </p>
          <div className="success-summary">
            <div className="summary-row">
              <span className="summary-label">Language</span>
              <span className="summary-value">{formData.language}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Name</span>
              <span className="summary-value">{formData.name}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Age / Gender</span>
              <span className="summary-value">{formData.age} years / {formData.gender}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">Symptoms</span>
              <span className="summary-value">{formData.symptoms.substring(0, 80)}{formData.symptoms.length > 80 ? '…' : ''}</span>
            </div>
          </div>
          <button className="btn-start-over" onClick={handleStartOver}>
            Start New Consultation
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="onboarding-container animate-fade-in">
      
      {/* Progress Bar */}
      <div className="progress-bar-wrapper">
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
        </div>
        <span className="progress-text">Step {step} of {totalSteps}</span>
      </div>

      {/* Step Indicators */}
      <div className="step-indicators">
        {[
          { num: 1, label: 'Language', icon: Globe },
          { num: 2, label: 'Profile', icon: User },
          { num: 3, label: 'Symptoms', icon: Activity },
          { num: 4, label: 'Review', icon: Sparkles },
        ].map(s => (
          <div key={s.num} className={`si-item ${step >= s.num ? 'active' : ''} ${step === s.num ? 'current' : ''}`}>
            <div className="si-circle">
              {step > s.num ? <CheckCircle2 size={16} /> : <s.icon size={16} />}
            </div>
            <span className="si-label">{s.label}</span>
          </div>
        ))}
      </div>

      <div className="onboarding-card">

        {/* ─── Step 1: Language ─── */}
        {step === 1 && (
          <div className="step-content animate-slide-up" key="step-1">
            <div className="step-icon-wrapper">
              <Globe size={28} />
            </div>
            <h2>Choose your language</h2>
            <p className="step-subtitle">Select the language you are most comfortable with</p>
            
            <div className="language-grid">
              {LANGUAGES.map(lang => (
                <button 
                  key={lang.code}
                  className={`lang-btn ${formData.language === lang.name ? 'selected' : ''}`}
                  onClick={() => handleSelectLanguage(lang)}
                >
                  <div className="lang-info">
                    <span className="lang-native">{lang.native}</span>
                    <span className="lang-english">{lang.name}</span>
                  </div>
                  {formData.language === lang.name && <CheckCircle2 size={18} className="lang-check" />}
                </button>
              ))}
            </div>

            <div className="step-actions">
              <button 
                className="btn-next" 
                onClick={handleNext}
                disabled={!formData.language}
              >
                Continue <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* ─── Step 2: Profile ─── */}
        {step === 2 && (
          <div className="step-content animate-slide-up" key="step-2">
            <div className="step-icon-wrapper">
              <User size={28} />
            </div>
            <h2>Your Information</h2>
            <p className="step-subtitle">Tell us a bit about yourself so we can help you better</p>
            
            <div className="form-group">
              <label htmlFor="patient-name">Full Name</label>
              <input 
                id="patient-name"
                type="text" 
                placeholder="Enter your full name"
                className="patient-input"
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                autoFocus
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="patient-age">Age</label>
                <input 
                  id="patient-age"
                  type="number" 
                  placeholder="Years"
                  className="patient-input"
                  min="1"
                  max="120"
                  value={formData.age}
                  onChange={e => setFormData({...formData, age: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label htmlFor="patient-gender">Gender</label>
                <select 
                  id="patient-gender"
                  className="patient-input"
                  value={formData.gender}
                  onChange={e => setFormData({...formData, gender: e.target.value})}
                >
                  <option value="">Select gender</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                  <option value="Prefer not to say">Prefer not to say</option>
                </select>
              </div>
            </div>

            <div className="step-actions two-btn">
              <button className="btn-back" onClick={handleBack}>
                <ArrowLeft size={16} /> Back
              </button>
              <button 
                className="btn-next" 
                onClick={handleNext}
                disabled={!formData.name || !formData.age || !formData.gender}
              >
                Continue <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* ─── Step 3: Symptoms ─── */}
        {step === 3 && (
          <div className="step-content animate-slide-up" key="step-3">
            <div className="step-icon-wrapper">
              <Activity size={28} />
            </div>
            <h2>Describe your symptoms</h2>
            <p className="step-subtitle">Type below or tap the microphone to speak in {formData.language || 'your language'}</p>
            
            <div className="symptoms-input-wrapper">
              <textarea 
                ref={textareaRef}
                placeholder="For example: I have been feeling feverish since yesterday, with body pain and headache..."
                className="patient-textarea"
                rows={6}
                value={formData.symptoms}
                onChange={e => setFormData({...formData, symptoms: e.target.value})}
                autoFocus
              />
              
              <div className="mic-area">
                <button 
                  className={`mic-btn ${isRecording ? 'recording' : ''}`}
                  onClick={toggleRecording}
                  title={isRecording ? 'Tap to stop' : 'Tap to speak'}
                >
                  {isRecording ? <MicOff size={22} /> : <Mic size={22} />}
                </button>
                <span className="mic-label">
                  {isRecording ? 'Listening… tap to stop' : 'Tap to speak'}
                </span>
              </div>
            </div>
            
            {isRecording && (
              <div className="recording-indicator">
                <span className="rec-dot" />
                <span>Recording in {formData.language}…</span>
              </div>
            )}

            <div className="step-actions two-btn">
              <button className="btn-back" onClick={handleBack}>
                <ArrowLeft size={16} /> Back
              </button>
              <button 
                className="btn-next" 
                onClick={handleNext}
                disabled={!formData.symptoms.trim()}
              >
                Review <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* ─── Step 4: Review & Submit ─── */}
        {step === 4 && (
          <div className="step-content animate-slide-up" key="step-4">
            <div className="step-icon-wrapper">
              <Sparkles size={28} />
            </div>
            <h2>Review your information</h2>
            <p className="step-subtitle">Please confirm everything looks correct before submitting</p>
            
            <div className="review-card">
              <div className="review-row">
                <span className="review-label">Language</span>
                <span className="review-value">{formData.language}</span>
              </div>
              <div className="review-divider" />
              <div className="review-row">
                <span className="review-label">Full Name</span>
                <span className="review-value">{formData.name}</span>
              </div>
              <div className="review-divider" />
              <div className="review-row">
                <span className="review-label">Age</span>
                <span className="review-value">{formData.age} years</span>
              </div>
              <div className="review-divider" />
              <div className="review-row">
                <span className="review-label">Gender</span>
                <span className="review-value">{formData.gender}</span>
              </div>
              <div className="review-divider" />
              <div className="review-row review-symptoms-row">
                <span className="review-label">Symptoms</span>
                <p className="review-symptoms-text">{formData.symptoms}</p>
              </div>
            </div>

            <div className="step-actions two-btn">
              <button className="btn-back" onClick={handleBack}>
                <ArrowLeft size={16} /> Back
              </button>
              <button className="btn-finish" onClick={handleSubmit}>
                <Send size={16} /> Submit
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
