import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { eventsAPI, clientsAPI } from '../services/api';
import { format } from 'date-fns';
import { Calendar, Plus, Filter } from 'lucide-react';

export default function Events() {
  const [events, setEvents] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ client: '', type: '' });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadEvents();
  }, [filter]);

  const loadData = async () => {
    try {
      const [eventsRes, clientsRes] = await Promise.all([
        eventsAPI.list({ limit: 100 }),
        clientsAPI.list({ limit: 100 }),
      ]);
      setEvents(eventsRes.data.events);
      setClients(clientsRes.data.clients);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadEvents = async () => {
    try {
      const params = { limit: 100 };
      if (filter.client) params.client_id = filter.client;
      if (filter.type) params.event_type = filter.type;

      const response = await eventsAPI.list(params);
      setEvents(response.data.events);
    } catch (error) {
      console.error('Error loading events:', error);
    }
  };

  const getClientName = (clientId) => {
    const client = clients.find(c => c.id === clientId);
    return client?.name || 'Unknown Client';
  };

  const getEventBadgeColor = (type) => {
    const colors = {
      meeting: 'badge-info',
      call: 'badge-warning',
      email: 'badge-success',
      other: 'badge-info',
    };
    return colors[type] || 'badge-info';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Events</h1>
        <Link to="/events/new" className="btn btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          Create Event
        </Link>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Client
            </label>
            <select
              value={filter.client}
              onChange={(e) => setFilter({ ...filter, client: e.target.value })}
              className="input"
            >
              <option value="">All Clients</option>
              {clients.map(client => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              value={filter.type}
              onChange={(e) => setFilter({ ...filter, type: e.target.value })}
              className="input"
            >
              <option value="">All Types</option>
              <option value="meeting">Meeting</option>
              <option value="call">Call</option>
              <option value="email">Email</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
      </div>

      {/* Events List */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Loading events...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-12">
          <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">No events found</p>
          <Link to="/events/new" className="mt-4 inline-block btn btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            Create First Event
          </Link>
        </div>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Client</th>
                <th>Type</th>
                <th>Date & Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td className="font-medium">{event.title}</td>
                  <td>{getClientName(event.client_id)}</td>
                  <td>
                    <span className={getEventBadgeColor(event.type)}>
                      {event.type}
                    </span>
                  </td>
                  <td>
                    {format(new Date(event.datetime), 'MMM d, yyyy HH:mm')}
                  </td>
                  <td>
                    <Link
                      to={`/events/${event.id}`}
                      className="text-primary-600 hover:text-primary-700 font-medium"
                    >
                      View Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
