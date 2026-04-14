import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { eventsAPI, clientsAPI } from '../services/api';
import { ArrowLeft, Edit, Trash2, Calendar as CalendarIcon, Building2, User, Clock, FileText, X, Upload, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';

const POLL_INTERVAL_MS = 2000;

export default function EventDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [event, setEvent] = useState(null);
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [showMediaModal, setShowMediaModal] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState(null);

  // Live transcription poll state
  const [transcription, setTranscription] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [progress, setProgress] = useState(0);
  const processingStartedAtRef = useRef(null);

  const pollTimerRef = useRef(null);
  const elapsedTimerRef = useRef(null);
  const progressTimerRef = useRef(null);
  const lastStatusRef = useRef(null);

  const loadEventData = useCallback(async () => {
    try {
      const eventRes = await eventsAPI.get(id);
      setEvent(eventRes.data);
      if (eventRes.data.client_id) {
        const clientRes = await clientsAPI.get(eventRes.data.client_id);
        setClient(clientRes.data);
      }
      return eventRes.data;
    } catch (err) {
      console.error('Error loading event:', err);
      setError(err.response?.data?.detail || 'Failed to load event');
      return null;
    }
  }, [id]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await loadEventData();
      setLoading(false);
    })();
  }, [loadEventData]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const stopElapsedTimer = useCallback(() => {
    if (elapsedTimerRef.current) {
      clearInterval(elapsedTimerRef.current);
      elapsedTimerRef.current = null;
    }
  }, []);

  const stopProgressTimer = useCallback(() => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  }, []);

  const pollTranscription = useCallback(async () => {
    try {
      const res = await eventsAPI.getTranscription(id);
      console.log('[transcription-poll]', res.data);
      setTranscription(res.data);

      const status = res.data.status;
      const prev = lastStatusRef.current;
      lastStatusRef.current = status;

      if (status === 'completed' || status === 'failed') {
        stopPolling();
        stopElapsedTimer();
        stopProgressTimer();
        setProgress(status === 'completed' ? 100 : 0);
        if (prev !== status) {
          await loadEventData();
        }
      }
    } catch (err) {
      console.error('Error polling transcription:', err);
    }
  }, [id, loadEventData, stopPolling, stopElapsedTimer, stopProgressTimer]);

  // When the event has audio/video media, poll status until completed/failed.
  useEffect(() => {
    if (!event) return;

    const audioVideo = (event.media || []).some(m => m.file_type === 'audio' || m.file_type === 'video');
    if (!audioVideo) return;

    pollTranscription();

    if (!pollTimerRef.current) {
      pollTimerRef.current = setInterval(pollTranscription, POLL_INTERVAL_MS);
    }

    return () => stopPolling();
  }, [event, pollTranscription, stopPolling]);

  // Drive elapsed timer + progress simulation while processing/pending.
  useEffect(() => {
    const status = transcription?.status;
    const active = status === 'processing' || status === 'pending';

    if (!active) {
      stopElapsedTimer();
      stopProgressTimer();
      processingStartedAtRef.current = null;
      setElapsedSeconds(0);
      if (status !== 'completed' && status !== 'failed') setProgress(0);
      return;
    }

    if (!processingStartedAtRef.current) {
      processingStartedAtRef.current = Date.now();
      setProgress(0);
    }

    const tick = () => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - processingStartedAtRef.current) / 1000)));
    };
    tick();
    if (!elapsedTimerRef.current) elapsedTimerRef.current = setInterval(tick, 1000);

    if (!progressTimerRef.current) {
      progressTimerRef.current = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 1000);
    }

    return () => {
      stopElapsedTimer();
      stopProgressTimer();
    };
  }, [transcription?.status, stopElapsedTimer, stopProgressTimer]);

  useEffect(() => () => {
    stopPolling();
    stopElapsedTimer();
    stopProgressTimer();
  }, [stopPolling, stopElapsedTimer, stopProgressTimer]);

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this event?')) return;
    try {
      await eventsAPI.delete(id);
      navigate('/events');
    } catch (err) {
      console.error('Error deleting event:', err);
      alert('Failed to delete event');
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const validExtensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.mp4', '.avi', '.mov', '.mkv', '.webm'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    if (!validExtensions.includes(fileExtension)) {
      alert('Invalid file type. Please upload an audio or video file.');
      return;
    }

    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
      alert('File too large. Maximum size is 500MB.');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      await eventsAPI.uploadMedia(id, formData);

      setTranscription({ status: 'pending', transcript: '', error: null });
      lastStatusRef.current = 'pending';
      processingStartedAtRef.current = Date.now();
      setProgress(0);

      await loadEventData();
    } catch (err) {
      console.error('Error uploading file:', err);
      alert('Failed to upload file: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const getEventTypeBadge = (type) => {
    const badges = {
      meeting: 'bg-blue-100 text-blue-800',
      call: 'bg-yellow-100 text-yellow-800',
      email: 'bg-green-100 text-green-800',
      other: 'bg-gray-100 text-gray-800',
    };
    return badges[type] || badges.other;
  };

  const handleMediaClick = (media) => {
    setSelectedMedia(media);
    setShowMediaModal(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-600">{error}</p>
          <Link to="/events" className="mt-4 inline-block text-primary-600 hover:underline">Back to Events</Link>
        </div>
      </div>
    );
  }

  if (!event) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-yellow-700">Event not found</p>
          <Link to="/events" className="mt-4 inline-block text-primary-600 hover:underline">Back to Events</Link>
        </div>
      </div>
    );
  }

  const eventDate = new Date(event.datetime);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <Link to="/events" className="inline-flex items-center text-gray-600 hover:text-gray-900">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Events
        </Link>
      </div>

      <div className="card">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-gray-900">{event.title}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${getEventTypeBadge(event.type)}`}>{event.type}</span>
            </div>
            <p className="text-sm text-gray-500">Event ID: {event.id}</p>
          </div>
          <div className="flex items-center space-x-2">
            <Link to={`/events/${id}/edit`} className="p-2 text-gray-400 hover:text-primary-600 transition-colors" title="Edit Event">
              <Edit className="w-5 h-5" />
            </Link>
            <button onClick={handleDelete} className="p-2 text-gray-400 hover:text-red-600 transition-colors" title="Delete Event">
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className="flex items-start space-x-3">
            <CalendarIcon className="w-5 h-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Date & Time</p>
              <p className="text-gray-600">{eventDate.toLocaleString()}</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <Building2 className="w-5 h-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Client</p>
              {client ? (
                <Link to={`/clients/${client.id}`} className="text-primary-600 hover:underline">{client.name}</Link>
              ) : (
                <p className="text-gray-600">N/A</p>
              )}
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <User className="w-5 h-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Created By</p>
              <p className="text-gray-600">{event.created_by_username || 'Unknown'}</p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <Clock className="w-5 h-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Created At</p>
              <p className="text-gray-600">{new Date(event.created_at).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {event.notes && (
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-2">
              <FileText className="w-5 h-5 text-gray-400" />
              <h3 className="text-sm font-medium text-gray-700">Notes</h3>
            </div>
            <p className="text-gray-600 whitespace-pre-wrap">{event.notes}</p>
          </div>
        )}

        {event.media && event.media.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Attached Files</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {event.media.map((media) => (
                <div key={media.id} onClick={() => handleMediaClick(media)} className="p-4 border rounded-lg cursor-pointer hover:border-primary-300 hover:bg-primary-50 transition-colors">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-gray-400" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{media.original_filename}</p>
                      <p className="text-xs text-gray-500">{(media.file_size / 1024).toFixed(1)} KB • {media.file_type}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Upload Audio/Video for Transcription</h3>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-primary-400 transition-colors">
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileUpload}
              accept=".mp3,.wav,.m4a,.ogg,.flac,.aac,.mp4,.avi,.mov,.mkv,.webm"
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              {uploading ? (
                <div className="flex items-center justify-center">
                  <Loader2 className="animate-spin w-6 h-6 text-primary-600" />
                  <span className="ml-3 text-gray-600">Uploading...</span>
                </div>
              ) : (
                <div>
                  <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-sm text-gray-600 mb-2">Click to upload</p>
                  <p className="text-xs text-gray-500">MP3, WAV, M4A, OGG, FLAC, AAC, MP4, AVI, MOV, MKV, WEBM (max 500MB)</p>
                </div>
              )}
            </label>
          </div>

          <TranscriptionCard
            transcription={transcription}
            elapsedSeconds={elapsedSeconds}
            progress={progress}
          />
        </div>

        {event.follow_ups && event.follow_ups.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Follow-ups</h3>
            <div className="space-y-2">
              {event.follow_ups.map((followUp) => (
                <div key={followUp.id} className="p-3 border rounded-lg">
                  <p className="text-sm text-gray-700">{followUp.description}</p>
                  {followUp.date && <p className="text-xs text-gray-500 mt-1">Due: {new Date(followUp.date).toLocaleDateString()}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {event.deadlines && event.deadlines.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">Deadlines</h3>
            <div className="space-y-2">
              {event.deadlines.map((deadline) => (
                <div key={deadline.id} className="p-3 border rounded-lg">
                  <p className="text-sm text-gray-700">{deadline.description}</p>
                  <p className="text-xs text-gray-500 mt-1">Due: {new Date(deadline.due_date).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {showMediaModal && selectedMedia && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{selectedMedia.original_filename}</h3>
              <button onClick={() => setShowMediaModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-4">
                File type: {selectedMedia.file_type}<br />
                Size: {(selectedMedia.file_size / 1024).toFixed(1)} KB
              </p>
              <button onClick={() => window.open(`/api/events/media/${selectedMedia.id}/download`, '_blank')} className="btn btn-primary">
                Download File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function TranscriptionCard({ transcription, elapsedSeconds, progress }) {
  if (!transcription || transcription.status === 'none') return null;

  const { status, transcript, error, language_code, confidence } = transcription;

  if (status === 'pending') {
    return (
      <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-md flex items-center gap-2">
        <Loader2 className="w-4 h-4 text-gray-500 animate-spin" />
        <span className="text-sm text-gray-700">Queued...</span>
      </div>
    );
  }

  if (status === 'processing') {
    return (
      <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
        <div className="flex items-center gap-2 mb-2">
          <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
          <span className="text-sm text-blue-700">
            Transcribing audio... ({elapsedSeconds}s)
          </span>
        </div>
        <div className="w-full h-2 bg-blue-100 rounded overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-1000 ease-linear"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    );
  }

  if (status === 'completed') {
    return (
      <div className="mt-3">
        <div className="p-3 bg-green-50 border border-green-200 rounded-md flex items-center gap-2 mb-3">
          <CheckCircle2 className="w-4 h-4 text-green-600" />
          <span className="text-sm text-green-700">Transcription ready</span>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-500">
              {language_code || 'unknown'} • Confidence: {confidence != null ? (confidence * 100).toFixed(1) + '%' : 'N/A'}
            </span>
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{transcript || '(empty)'}</p>
        </div>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600" />
          <span className="text-sm font-medium text-red-700">Transcription failed</span>
        </div>
        {error && <p className="mt-1 text-xs text-red-600 break-words">{error}</p>}
      </div>
    );
  }

  return null;
}
