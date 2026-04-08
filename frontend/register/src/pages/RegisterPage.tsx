import { useState, useRef, useCallback } from 'react'
import Webcam from 'react-webcam'
import { Camera, Upload, AlertCircle, Loader2, CheckCircle2, ScanLine } from 'lucide-react'
import { submitRegistration, ocrExtract } from '@walkforpeace/shared'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from '../i18n/useTranslation'

export default function RegisterPage() {
  const { t, lang, toggleLang } = useTranslation()
  const navigate = useNavigate()

  const MEDIA_TYPES = [
    { value: 'print', label: t('mediaType.print') },
    { value: 'tv', label: t('mediaType.tv') },
    { value: 'radio', label: t('mediaType.radio') },
    { value: 'online', label: t('mediaType.online') },
    { value: 'photographer', label: t('mediaType.photographer') },
    { value: 'freelance', label: t('mediaType.freelance') },
  ]

  const [form, setForm] = useState({
    full_name: '',
    organization: '',
    designation: '',
    email: '',
    phone: '',
    country: '',
    media_type: '',
    id_type: 'NIC',
    id_number: '',
    terms_accepted: false,
  })

  const [idDocument, setIdDocument] = useState<File | null>(null)
  const [idFaceCrop, setIdFaceCrop] = useState<File | null>(null)
  const [facePhoto, setFacePhoto] = useState<string | null>(null)
  const [faceBlob, setFaceBlob] = useState<Blob | null>(null)
  const [showCamera, setShowCamera] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [ocrLoading, setOcrLoading] = useState(false)
  const [ocrMessage, setOcrMessage] = useState('')
  const [error, setError] = useState('')
  const webcamRef = useRef<Webcam>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  const handleIdDocumentChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null
    setIdDocument(file)
    setOcrMessage('')

    if (file) {
      setOcrLoading(true)
      try {
        const result = await ocrExtract(file)
        if (result.id_number) {
          setForm(prev => ({ ...prev, id_number: result.id_number! }))
          if (result.name) {
            setForm(prev => ({ ...prev, id_number: result.id_number!, full_name: result.name! }))
            setOcrMessage('ID number and name extracted automatically')
          } else {
            setOcrMessage('ID number extracted automatically')
          }
        } else {
          setOcrMessage('Could not extract ID number automatically -- please enter it manually.')
        }
      } catch {
        setOcrMessage('OCR failed — please enter your ID number manually.')
      } finally {
        setOcrLoading(false)
      }
    }
  }

  const capturePhoto = useCallback(() => {
    const imageSrc = webcamRef.current?.getScreenshot()
    if (imageSrc) {
      setFacePhoto(imageSrc)
      fetch(imageSrc)
        .then(r => r.blob())
        .then(blob => setFaceBlob(blob))
      setShowCamera(false)
    }
  }, [webcamRef])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!idDocument) return setError(t('register.errorIdDoc'))
    if (!idFaceCrop) return setError(t('register.errorIdFace'))
    if (!faceBlob) return setError(t('register.errorFace'))
    if (!form.terms_accepted) return setError(t('register.errorTerms'))

    setSubmitting(true)
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => fd.append(k, String(v)))
      fd.append('id_document', idDocument)
      fd.append('id_face_crop', idFaceCrop)
      fd.append('face_photo', new File([faceBlob], 'face.jpg', { type: 'image/jpeg' }))

      const result = await submitRegistration(fd)
      navigate('/confirm', {
        state: {
          pin_code: result.pin_code,
          ref_number: result.ref_number,
          qr_code_url: result.qr_code_url,
        },
      })
    } catch (err: any) {
      setError(err.response?.data?.detail || t('register.errorGeneric'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-navy text-white py-6">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <Link to="/" className="inline-block">
            <h1 className="text-2xl font-bold text-saffron">Walk for Peace Sri Lanka</h1>
          </Link>
          <p className="text-gold text-sm">{t('register.title')}</p>
          <button
            onClick={toggleLang}
            className="mt-2 text-sm border border-gold/30 px-3 py-1 rounded-full text-gold hover:bg-gold/10 transition"
          >
            {lang === 'en' ? 'සිංහල' : 'EN'}
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="max-w-2xl mx-auto px-4 py-8">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Personal Information */}
        <section className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-navy mb-4">{t('register.personal')}</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('register.fullName')} *
              </label>
              <input
                name="full_name"
                value={form.full_name}
                onChange={handleChange}
                required
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('register.email')} *
              </label>
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                required
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('register.organization')} *
              </label>
              <input
                name="organization"
                value={form.organization}
                onChange={handleChange}
                required
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('register.designation')} *
              </label>
              <input
                name="designation"
                value={form.designation}
                onChange={handleChange}
                required
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('register.phone')} *
              </label>
              <input
                name="phone"
                value={form.phone}
                onChange={handleChange}
                required
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('register.country')} *
              </label>
              <input
                name="country"
                value={form.country}
                onChange={handleChange}
                required
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent"
              />
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('register.mediaType')} *
            </label>
            <select
              name="media_type"
              value={form.media_type}
              onChange={handleChange}
              required
              className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent"
            >
              <option value="">{t('register.selectMediaType')}</option>
              {MEDIA_TYPES.map(mt => (
                <option key={mt.value} value={mt.value}>
                  {mt.label}
                </option>
              ))}
            </select>
          </div>
        </section>

        {/* ID Document Upload with OCR */}
        <section className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-navy mb-4">{t('register.identity')}</h2>

          {/* ID Type + Number */}
          <div className="grid md:grid-cols-2 gap-4 mb-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">ID Type *</label>
              <select
                name="id_type"
                value={form.id_type}
                onChange={handleChange}
                className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent"
              >
                <option value="NIC">NIC</option>
                <option value="Passport">Passport</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {form.id_type === 'NIC' ? 'NIC Number' : 'Passport Number'} *
              </label>
              <div className="relative">
                <input
                  name="id_number"
                  value={form.id_number}
                  onChange={handleChange}
                  required
                  placeholder={form.id_type === 'NIC' ? 'e.g. 199012345678' : 'e.g. N1234567'}
                  className="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-saffron focus:border-transparent pr-8"
                />
                {ocrLoading && (
                  <Loader2 className="w-4 h-4 animate-spin text-saffron absolute right-2.5 top-2.5" />
                )}
              </div>
              {ocrMessage && (
                <p
                  className={`text-xs mt-1.5 flex items-center gap-1 ${
                    ocrMessage.includes('extracted') ? 'text-green-600' : 'text-amber-600'
                  }`}
                >
                  {ocrMessage.includes('extracted') ? (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  ) : (
                    <ScanLine className="w-3.5 h-3.5" />
                  )}
                  {ocrMessage}
                </p>
              )}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-4">
            {/* Full ID — triggers OCR */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('register.idDocument')} *
              </label>
              <label className="flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-6 cursor-pointer hover:border-saffron transition">
                {ocrLoading ? (
                  <Loader2 className="w-8 h-8 text-saffron animate-spin mb-2" />
                ) : (
                  <Upload className="w-8 h-8 text-gray-400 mb-2" />
                )}
                <span className="text-sm text-gray-500 text-center">
                  {idDocument
                    ? idDocument.name
                    : t('register.idDocumentHint')}
                </span>
                {!idDocument && (
                  <span className="text-xs text-saffron mt-1 flex items-center gap-1">
                    <ScanLine className="w-3 h-3" /> OCR will auto-fill ID number
                  </span>
                )}
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  className="hidden"
                  onChange={handleIdDocumentChange}
                />
              </label>
            </div>

            {/* Face crop from ID */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('register.idFaceCrop')} *
              </label>
              <label className="flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-6 cursor-pointer hover:border-saffron transition">
                <Upload className="w-8 h-8 text-gray-400 mb-2" />
                <span className="text-sm text-gray-500">
                  {idFaceCrop ? idFaceCrop.name : t('register.idFaceCropHint')}
                </span>
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={e => setIdFaceCrop(e.target.files?.[0] || null)}
                />
              </label>
            </div>
          </div>

          <p className="text-xs text-gray-400">{t('register.idTip')}</p>
        </section>

        {/* Live Face Capture */}
        <section className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-navy mb-2">{t('register.livePhoto')} *</h2>
          <p className="text-sm text-gray-500 mb-4">{t('register.livePhotoHint')}</p>

          {facePhoto ? (
            <div className="text-center">
              <img
                src={facePhoto}
                alt="Captured face"
                className="w-48 h-48 object-cover rounded-xl mx-auto border-2 border-green-400"
              />
              <button
                type="button"
                onClick={() => {
                  setFacePhoto(null)
                  setFaceBlob(null)
                  setShowCamera(true)
                }}
                className="mt-3 text-saffron hover:underline text-sm"
              >
                {t('register.retake')}
              </button>
            </div>
          ) : showCamera ? (
            <div className="text-center">
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                screenshotQuality={0.9}
                videoConstraints={{ facingMode: 'user', width: 640, height: 480 }}
                className="rounded-xl mx-auto max-w-sm"
              />
              <button
                type="button"
                onClick={capturePhoto}
                className="mt-4 bg-saffron text-white px-6 py-2 rounded-lg font-medium hover:bg-saffron-dark transition"
              >
                <Camera className="inline w-4 h-4 mr-2" />
                {t('register.capture')}
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowCamera(true)}
              className="w-full border-2 border-dashed rounded-lg p-8 text-center hover:border-saffron transition"
            >
              <Camera className="w-10 h-10 text-gray-400 mx-auto mb-2" />
              <span className="text-gray-500">{t('register.openCamera')}</span>
            </button>
          )}
        </section>

        {/* Terms & Submit */}
        <section className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              name="terms_accepted"
              checked={form.terms_accepted}
              onChange={handleChange}
              className="mt-1 w-4 h-4 rounded border-gray-300 text-saffron focus:ring-saffron"
            />
            <span className="text-sm text-gray-600">{t('register.terms')}</span>
          </label>
        </section>

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-saffron text-white py-3 rounded-xl font-semibold text-lg hover:bg-saffron-dark transition disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {submitting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" /> {t('register.submitting')}
            </>
          ) : (
            t('register.submit')
          )}
        </button>
      </form>
    </div>
  )
}
