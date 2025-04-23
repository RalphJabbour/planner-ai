import React from 'react';
import PropTypes from 'prop-types';

const slotHeight = 60; // px per hour slot
const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const parseTime = time => {
  const [h, m] = time.split(':').map(Number);
  return h + m / 60;
};

const WeeklyCalendar = ({ events }) => {
  // group events by day index
  const eventsByDay = {};
  events.forEach(ev => {
    if (!eventsByDay[ev.day]) eventsByDay[ev.day] = [];
    eventsByDay[ev.day].push(ev);
  });

  return (
    <div className="w-full flex flex-col">
      {/* Day headers */}
      <div className="grid grid-cols-7 text-center border-b border-gray-300">
        {days.map((d, idx) => (
          <div key={idx} className="py-2 font-medium">
            {d}
          </div>
        ))}
      </div>

      {/* Calendar body */}
      <div className="w-full flex overflow-y-scroll" style={{ height: '600px' }}>
        {days.map((_, dayIdx) => (
          <div key={dayIdx} className="flex-1 border-r border-gray-200 relative">
            {/* hourly grid lines */}
            {Array.from({ length: 24 }).map((_, hour) => (
              <div
                key={hour}
                className="h-[60px] border-b border-gray-200"
              />
            ))}

            {/* events */}
            {(eventsByDay[dayIdx] || []).map(ev => {
              const start = parseTime(ev.startTime);
              const end = parseTime(ev.endTime);
              const top = start * slotHeight;
              const height = (end - start) * slotHeight;
              const style = {
                position: 'absolute',
                top,
                height,
                left: 4,
                right: 4,
                backgroundColor: ev.color || '#3b82f6',
              };

              return (
                <div
                  key={ev.id}
                  className="p-1 rounded-md shadow-md text-white text-sm overflow-hidden"
                  style={style}
                  title={`${ev.title}${ev.location ? ` @ ${ev.location}` : ''}`}
                >
                  <div className="font-semibold truncate">{ev.title}</div>
                  {ev.location && <div className="truncate">{ev.location}</div>}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};

WeeklyCalendar.propTypes = {
  events: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      day: PropTypes.number.isRequired,      // 0=Sunday
      startTime: PropTypes.string.isRequired, // "HH:mm"
      endTime: PropTypes.string.isRequired,   // "HH:mm"
      title: PropTypes.string.isRequired,
      location: PropTypes.string,
      description: PropTypes.string,
      color: PropTypes.string,
    })
  ).isRequired,
};

export default WeeklyCalendar;