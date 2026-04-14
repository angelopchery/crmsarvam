import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Calendar, momentLocalizer, Views } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { eventsAPI, intelligenceAPI } from '../services/api';
import { Check, Clock } from 'lucide-react';

// Setup localizer
const localizer = momentLocalizer(moment);

export default function CalendarPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState(Views.WEEK);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Fetch both events and tasks in parallel
      const [eventsRes, tasksRes] = await Promise.all([
        eventsAPI.list({ limit: 100 }),
        intelligenceAPI.tasks.list({ limit: 100 }),
      ]);

      const fetchedEvents = eventsRes.data.events || [];
      const fetchedTasks = tasksRes.data || [];
      setTasks(fetchedTasks);

      console.log('Fetched events:', fetchedEvents);
      console.log('Fetched tasks:', fetchedTasks);

      // Convert events to calendar format
      const eventCalendarItems = fetchedEvents.map(event => {
        const startDate = new Date(event.datetime);
        const endDate = new Date(startDate.getTime() + 60 * 60 * 1000); // Add 1 hour default

        const calendarEvent = {
          id: `event-${event.id}`,
          title: event.title,
          start: startDate,
          end: endDate,
          resource: {
            type: 'event',
            data: event,
          },
        };

        console.log('Converted event to calendar:', calendarEvent);
        return calendarEvent;
      });

      // Convert pending tasks to calendar format
      const taskCalendarItems = fetchedTasks
        .filter(task => task.status === 'pending')
        .map(task => {
          const startDate = new Date(task.deadline_due_date);
          const endDate = new Date(new Date(task.deadline_due_date).setHours(23, 59, 59));

          return {
            id: `task-${task.id}`,
            title: `Deadline: ${task.deadline_description}`,
            start: startDate,
            end: endDate,
            resource: {
              type: 'task',
              data: task,
            },
          };
        });

      const allCalendarEvents = [...eventCalendarItems, ...taskCalendarItems];
      console.log('All calendar events:', allCalendarEvents);

      setEvents(allCalendarEvents);
    } catch (error) {
      console.error('Error loading calendar data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectEvent = useCallback((calendarEvent) => {
    console.log('Selected calendar event:', calendarEvent);

    // Navigate based on resource type
    if (calendarEvent.resource?.type === 'event') {
      navigate(`/events/${calendarEvent.resource.data.id}`);
    } else if (calendarEvent.resource?.type === 'task') {
      navigate(`/events/${calendarEvent.resource.data.event_id}`);
    } else {
      // Fallback for tasks (old format)
      navigate(`/events/${calendarEvent.resource.event_id}`);
    }
  }, [navigate]);

  const handleToggleTaskStatus = async (task) => {
    try {
      const newStatus = task.status === 'pending' ? 'completed' : 'pending';
      await intelligenceAPI.tasks.update(task.id, { status: newStatus });
      loadData(); // Reload data
    } catch (error) {
      console.error('Error updating task:', error);
      alert('Failed to update task status');
    }
  };

  const CustomEvent = ({ event }) => {
    const isTask = event.resource?.type === 'task';
    const isCompleted = isTask && event.resource?.data?.status === 'completed';

    return (
      <div className="text-xs">
        <div className="font-medium truncate">{event.title}</div>
        {!isTask && (
          <div className="mt-1 text-xs text-gray-400 capitalize">
            {event.resource?.data?.type || 'event'}
          </div>
        )}
        {isTask && (
          <div className="flex items-center mt-1">
            {isCompleted ? (
              <Check className="w-3 h-3 mr-1 text-green-600" />
            ) : (
              <Clock className="w-3 h-3 mr-1 text-yellow-600" />
            )}
            <span className="capitalize">{event.resource?.data?.status || 'pending'}</span>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading calendar...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Calendar</h1>
        <Link to="/events/new" className="btn btn-primary">
          Create Event
        </Link>
      </div>

      {/* Calendar */}
      <div className="card">
        <div className="h-[600px]">
          <Calendar
            localizer={localizer}
            events={events}
            startAccessor="start"
            endAccessor="end"
            views={[Views.MONTH, Views.WEEK, Views.DAY, Views.AGENDA]}
            view={view}
            onView={setView}
            onSelectEvent={handleSelectEvent}
            components={{
              event: CustomEvent,
            }}
            eventPropGetter={(event) => {
              const isTask = event.resource?.type === 'task';
              const isCompleted = isTask && event.resource?.data?.status === 'completed';

              return {
                className: isCompleted
                  ? 'bg-green-500'
                  : isTask
                  ? 'bg-yellow-500'
                  : 'bg-primary-500',
              };
            }}
            style={{
              height: '100%',
            }}
          />
        </div>
      </div>

      {/* Tasks List */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          All Tasks
        </h3>
        <div className="space-y-2">
          {tasks.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No tasks found</p>
          ) : (
            tasks.map((task) => (
              <div
                key={task.id}
                className={`flex items-center justify-between p-4 border rounded-lg ${
                  task.status === 'completed' ? 'border-green-200 bg-green-50' : 'border-gray-200'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/events/${task.event_id}`}
                    className="font-medium text-gray-900 hover:text-primary-600"
                  >
                    {task.event_title || 'Untitled Event'}
                  </Link>
                  <p className="text-sm text-gray-500 truncate">
                    {task.deadline_description}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Due: {new Date(task.deadline_due_date).toLocaleDateString()}
                  </p>
                </div>
                <div className="ml-4 flex items-center space-x-2">
                  <span className={`badge ${
                    task.status === 'completed' ? 'badge-success' : 'badge-warning'
                  }`}>
                    {task.status}
                  </span>
                  <button
                    onClick={() => handleToggleTaskStatus(task)}
                    className="btn btn-secondary text-xs"
                  >
                    {task.status === 'pending' ? 'Mark Complete' : 'Mark Pending'}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
