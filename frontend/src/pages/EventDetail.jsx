import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { eventsAPI, clientsAPI } from '../services/api';
import { ArrowLeft, Edit, Trash2, Calendar as CalendarIcon, Building2, User, Clock, FileText, X } from 'lucide-react';

export default function EventDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [client, setClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showMediaModal, setShowMediaModal] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState(null);

  useEffect(() => {
    loadEventData();
  }, [id]);

  const loadEventData = async () => {
    try {
      console.log('Token:', localStorage.getItem('token'));
      setLoading(true);

      // Get event with full details
      const eventRes = await eventsAPI.get(id);
      console.log('Event data:', eventRes.data);
      setEvent(eventRes.data);

      // Get client info if client_id exists
      if (eventRes.data.client_id) {
        const clientRes = await clientsAPI.get(eventRes.data.client_id);
        setClient(clientRes.data);
      }
    } catch (err) {
      console.error('Error loading event:', err);
      console.error('Error response:', err.response?.data);
      setError(err.response?.data?.detail || 'Failed to load event');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this event?')) {
      return;
    }

    try {
      await eventsAPI.delete(id);
      navigate('/events');
    } catch (err) {
      console.error('Error deleting event:', err);
      alert('Failed to delete event');
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
          <Link to="/events" className="mt-4 inline-block text-primary-600 hover:underline">
            Back to Events
          </Link>
        </div>
      </div>
    );
  }

  if (!event) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-yellow-700">Event not found</p>
          <Link to="/events" className="mt-4 inline-block text-primary-600 hover:underline">
            Back to Events
          </Link>
        </div>
      </div>
    );
  }

  const eventDate = new Date(event.datetime);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/events"
          className="inline-flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Events
        </Link>
      </div>

      <div className="card">
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-gray-900">{event.title}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${getEventTypeBadge(event.type)}`}>
                {event.type}
              </span>
            </div>
            <p className="text-sm text-gray-500">Event ID: {event.id}</p>
          </div>
          <div className="flex items-center space-x-2">
            <Link
              to={`/events/${id}/edit`}
              className="p-2 text-gray-400 hover:text-primary-600 transition-colors"
              title="Edit Event"
            >
              <Edit className="w-5 h-5" />
            </Link>
            <button
              onClick={handleDelete}
              className="p-2 text-gray-400 hover:text-red-600 transition-colors"
              title="Delete Event"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Event Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Date & Time */}
          <div className="flex items-start space-x-3">
            <CalendarIcon className="w-5 h-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Date & Time</p>
              <p className="text-gray-600">{eventDate.toLocaleString()}</p>
            </div>
          </div>

          {/* Client */}
          <div className="flex items-start space-x-3">
            <Building2 className="w-5 h-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Client</p>
              {client ? (
                <Link
                  to={`/clients/${client.id}`}
                  className="text-primary-600 hover:underline"
                >
                  {client.name}
                </Link>
              ) : (
                <p className="text-gray-600">N/A</p>
              )}
            </div>
          </div>

          {/* Created By */}
          <div className="flex items-start space-x-3">
            <User className="w-5 h-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Created By</p>
              <p className="text-gray-600">{event.created_by_username || 'Unknown'}</p>
            </div>
          </div>

          {/* Created At */}
          <div className="flex items-start space-x-3">
            <Clock className="w-5 h-5 text-gray-400 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-700">Created At</p>
              <p className="text-gray-600">{new Date(event.created_at).toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* Notes */}
        {event.notes && (
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-2">
              <FileText className="w-5 h-5 text-gray-400" />
              <h3 className="text-sm font-medium text-gray-700">Notes</h3>
            </div>
            <p className="text-gray-600 whitespace-pre-wrap">{event.notes}</p>
          </div>
        )}

        {/* Media Files */}
        {event.media && event.media.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Attached Files</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {event.media.map((media) => (
                <div
                  key={media.id}
                  onClick={() => handleMediaClick(media)}
                  className="p-4 border rounded-lg cursor-pointer hover:border-primary-300 hover:bg-primary-50 transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-gray-400" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {media.original_filename}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(media.file_size / 1024).toFixed(1)} KB • {media.file_type}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Transcriptions */}
        {event.transcriptions && event.transcriptions.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Transcriptions</h3>
            <div className="space-y-3">
              {event.transcriptions.map((trans) => (
                <div key={trans.id} className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-gray-500">
                      {trans.language_code} • Confidence: {trans.confidence ? (trans.confidence * 100).toFixed(1) : 'N/A'}%
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">{trans.transcript_text}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Follow-ups */}
        {event.follow_ups && event.follow_ups.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Follow-ups</h3>
            <div className="space-y-2">
              {event.follow_ups.map((followUp) => (
                <div key={followUp.id} className="p-3 border rounded-lg">
                  <p className="text-sm text-gray-700">{followUp.description}</p>
                  {followUp.date && (
                    <p className="text-xs text-gray-500 mt-1">
                      Due: {new Date(followUp.date).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Deadlines */}
        {event.deadlines && event.deadlines.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">Deadlines</h3>
            <div className="space-y-2">
              {event.deadlines.map((deadline) => (
                <div key={deadline.id} className="p-3 border rounded-lg">
                  <p className="text-sm text-gray-700">{deadline.description}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Due: {new Date(deadline.due_date).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Media Modal */}
      {showMediaModal && selectedMedia && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{selectedMedia.original_filename}</h3>
              <button
                onClick={() => setShowMediaModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-4">
                File type: {selectedMedia.file_type}<br />
                Size: {(selectedMedia.file_size / 1024).toFixed(1)} KB
              </p>
              <button
                onClick={() => {
                  // Download the file
                  window.open(`/api/events/media/${selectedMedia.id}/download`, '_blank');
                }}
                className="btn btn-primary"
              >
                Download File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
