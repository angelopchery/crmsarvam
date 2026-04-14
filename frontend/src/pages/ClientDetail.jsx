import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { clientsAPI, eventsAPI } from '../services/api';
import { ArrowLeft, Edit, Trash2, Calendar as CalendarIcon, Building2 } from 'lucide-react';

export default function ClientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [client, setClient] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadClientData();
  }, [id]);

  const loadClientData = async () => {
    try {
      setLoading(true);
      const [clientRes, eventsRes] = await Promise.all([
        clientsAPI.get(id),
        eventsAPI.list({ client_id: id, limit: 10 }),
      ]);
      setClient(clientRes.data);
      setEvents(eventsRes.data.events || []);
    } catch (err) {
      console.error('Error loading client:', err);
      setError(err.response?.data?.detail || 'Failed to load client');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this client? This will also delete all associated data.')) {
      return;
    }

    try {
      await clientsAPI.delete(id);
      navigate('/clients');
    } catch (err) {
      console.error('Error deleting client:', err);
      alert('Failed to delete client');
    }
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
          <Link to="/clients" className="mt-4 inline-block text-primary-600 hover:underline">
            Back to Clients
          </Link>
        </div>
      </div>
    );
  }

  if (!client) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-yellow-700">Client not found</p>
          <Link to="/clients" className="mt-4 inline-block text-primary-600 hover:underline">
            Back to Clients
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/clients"
          className="inline-flex items-center text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Clients
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Client Details */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center">
                <div className="p-3 bg-primary-100 rounded-lg mr-4">
                  <Building2 className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">{client.name}</h1>
                  <p className="text-sm text-gray-500">ID: {client.id}</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Link
                  to={`/clients/${id}/edit`}
                  className="p-2 text-gray-400 hover:text-primary-600 transition-colors"
                  title="Edit Client"
                >
                  <Edit className="w-5 h-5" />
                </Link>
                <button
                  onClick={handleDelete}
                  className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                  title="Delete Client"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>

            {client.description && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">Description</h3>
                <p className="text-gray-600">{client.description}</p>
              </div>
            )}

            <div className="pt-4 border-t border-gray-200">
              <p className="text-sm text-gray-500">
                Created on {new Date(client.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          {/* Events */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <CalendarIcon className="w-5 h-5 text-gray-600 mr-2" />
                <h2 className="text-lg font-semibold text-gray-900">Recent Events</h2>
              </div>
              <Link
                to="/events/new"
                className="btn btn-secondary text-sm"
              >
                Add Event
              </Link>
            </div>

            {events.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No events yet</p>
            ) : (
              <div className="space-y-3">
                {events.map((event) => (
                  <Link
                    key={event.id}
                    to={`/events/${event.id}`}
                    className="block p-3 border rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-gray-900">{event.title}</h4>
                        <p className="text-sm text-gray-500">
                          {new Date(event.datetime).toLocaleString()}
                        </p>
                      </div>
                      <span className="text-xs px-2 py-1 bg-gray-100 rounded-full capitalize">
                        {event.type}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="card">
            <h3 className="text-sm font-medium text-gray-700 mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <Link
                to={`/clients/${id}/edit`}
                className="w-full btn btn-secondary text-sm"
              >
                <Edit className="w-4 h-4 mr-2 inline" />
                Edit Client
              </Link>
              <Link
                to="/events/new"
                className="w-full btn btn-secondary text-sm"
              >
                <CalendarIcon className="w-4 h-4 mr-2 inline" />
                Add Event
              </Link>
            </div>
          </div>

          <div className="card">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Client Statistics</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Total Events</span>
                <span className="font-semibold">{events.length}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
