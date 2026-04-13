import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { clientsAPI } from '../services/api';
import { Building2, Plus, Search, Edit, Trash2 } from 'lucide-react';

export default function Clients() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadClients();
  }, [searchTerm]);

  const loadClients = async () => {
    try {
      setLoading(true);
      const response = await clientsAPI.list({
        search: searchTerm || undefined,
        limit: 100,
      });
      setClients(response.data.clients);
    } catch (error) {
      console.error('Error loading clients:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this client?')) {
      return;
    }

    try {
      await clientsAPI.delete(id);
      loadClients();
    } catch (error) {
      console.error('Error deleting client:', error);
      alert('Failed to delete client');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
        <Link to="/clients/new" className="btn btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          Add Client
        </Link>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search clients..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input pl-10"
        />
      </div>

      {/* Clients List */}
      {loading ? (
        <div className="text-center py-8 text-gray-500">Loading clients...</div>
      ) : clients.length === 0 ? (
        <div className="text-center py-12">
          <Building2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">No clients found</p>
          <Link to="/clients/new" className="mt-4 inline-block btn btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            Add First Client
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {clients.map((client) => (
            <div key={client.id} className="card">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/clients/${client.id}`}
                    className="text-lg font-semibold text-gray-900 hover:text-primary-600"
                  >
                    {client.name}
                  </Link>
                  {client.description && (
                    <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                      {client.description}
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-4 flex items-center space-x-2">
                <Link
                  to={`/clients/${client.id}`}
                  className="btn btn-secondary text-xs"
                >
                  View Details
                </Link>
                <Link
                  to={`/clients/${client.id}/edit`}
                  className="p-2 text-gray-400 hover:text-primary-600 transition-colors"
                >
                  <Edit className="w-4 h-4" />
                </Link>
                <button
                  onClick={() => handleDelete(client.id)}
                  className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
