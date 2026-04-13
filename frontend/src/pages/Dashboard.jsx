import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { clientsAPI, intelligenceAPI } from '../services/api';
import { format } from 'date-fns';
import {
  Building2,
  Calendar as CalendarIcon,
  Clock,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState({
    clients: 0,
    upcomingTasks: 0,
    pendingTasks: 0,
    completedTasks: 0,
  });
  const [recentTasks, setRecentTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      // Load clients count
      const clientsResponse = await clientsAPI.list({ limit: 1 });
      setStats(prev => ({ ...prev, clients: clientsResponse.data.total }));

      // Load tasks
      const tasksResponse = await intelligenceAPI.tasks.list({ limit: 10 });
      const tasks = tasksResponse.data;

      setStats(prev => ({
        ...prev,
        upcomingTasks: tasks.length,
        pendingTasks: tasks.filter(t => t.status === 'pending').length,
        completedTasks: tasks.filter(t => t.status === 'completed').length,
      }));

      // Sort by due date and take recent
      const sortedTasks = tasks
        .sort((a, b) => new Date(a.deadline_due_date) - new Date(b.deadline_due_date))
        .slice(0, 5);
      setRecentTasks(sortedTasks);
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  const statCards = [
    {
      name: 'Total Clients',
      value: stats.clients,
      icon: Building2,
      color: 'bg-blue-500',
      href: '/clients',
    },
    {
      name: 'Upcoming Tasks',
      value: stats.upcomingTasks,
      icon: CalendarIcon,
      color: 'bg-purple-500',
      href: '/calendar',
    },
    {
      name: 'Pending Tasks',
      value: stats.pendingTasks,
      icon: Clock,
      color: 'bg-yellow-500',
      href: '/calendar',
    },
    {
      name: 'Completed Tasks',
      value: stats.completedTasks,
      icon: CheckCircle2,
      color: 'bg-green-500',
      href: '/calendar',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Link
            key={stat.name}
            to={stat.href}
            className="card hover:shadow-md transition-shadow"
          >
            <div className="flex items-center">
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Recent Tasks */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Upcoming Tasks
        </h3>

        {recentTasks.length === 0 ? (
          <div className="text-center py-8">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-2" />
            <p className="text-gray-500">No upcoming tasks</p>
            <Link
              to="/events/new"
              className="mt-4 inline-block btn btn-primary"
            >
              Create Event
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {recentTasks.map((task) => (
              <div
                key={task.id}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/events/${task.event_id}`}
                    className="text-sm font-medium text-gray-900 hover:text-primary-600"
                  >
                    {task.event_title || 'Untitled Event'}
                  </Link>
                  <p className="text-sm text-gray-500 truncate">
                    {task.deadline_description}
                  </p>
                </div>

                <div className="ml-4 flex items-center space-x-4">
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">
                      {format(new Date(task.deadline_due_date), 'MMM d, yyyy')}
                    </p>
                    <span className={`badge ${
                      task.status === 'completed' ? 'badge-success' : 'badge-warning'
                    }`}>
                      {task.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {recentTasks.length > 0 && (
          <div className="mt-4 text-center">
            <Link to="/calendar" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
              View all tasks →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
