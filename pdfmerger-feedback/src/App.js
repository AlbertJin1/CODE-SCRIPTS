// src/App.js
import { useState, useEffect, useMemo, useRef } from 'react';
import { supabase } from './supabaseClient';
import './index.css';
import { Helmet } from 'react-helmet';
import supabaseLogo from './icons/supabase.png';

// === REALTIME MANILA CLOCK ===
const ManilaClock = () => {
  const [time, setTime] = useState('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const manilaTime = now.toLocaleString('en-PH', {
        timeZone: 'Asia/Manila',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
      setTime(manilaTime);
    };

    updateClock();
    const interval = setInterval(updateClock, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 text-xs font-medium text-gray-600 bg-white px-3 py-1 rounded-full shadow-sm">
      <img
        src="https://cdn-icons-png.flaticon.com/512/54/54158.png"
        alt="Clock"
        className="w-4 h-4"
      />
      <span>{time}</span>
      <span className="text-gray-400">GMT+8</span>
    </div>
  );
};

// Star component (read-only)
const StarRating = ({ rating }) => {
  return (
    <div className="flex space-x-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <span
          key={star}
          className={`text-lg ${star <= rating ? 'text-yellow-400' : 'text-gray-300'}`}
        >
          ★
        </span>
      ))}
    </div>
  );
};

// Format date in Manila time (GMT+8)
const formatManilaTime = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleString('en-PH', {
    timeZone: 'Asia/Manila',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export default function App() {
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterRating, setFilterRating] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;
  const subscriptionRef = useRef(null);

  // Fetch initial feedback
  useEffect(() => {
    const fetchFeedback = async () => {
      setLoading(true);
      setError('');

      const { data, error } = await supabase
        .from('feedback')
        .select('id, rating, name, comment, created_at')
        .order('created_at', { ascending: false });

      if (error) {
        setError('Failed to load feedback.');
        console.error(error);
      } else {
        setFeedback(data || []);
      }
      setLoading(false);
    };

    fetchFeedback();
  }, []);

  // === REALTIME SUBSCRIPTION ===
  useEffect(() => {
    if (subscriptionRef.current) {
      supabase.removeChannel(subscriptionRef.current);
    }

    const channel = supabase
      .channel('public:feedback')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'feedback',
        },
        (payload) => {
          const newFeedback = payload.new;
          setFeedback((prev) => {
            if (prev.some(f => f.id === newFeedback.id)) return prev;
            return [newFeedback, ...prev];
          });
        }
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log('Realtime subscribed');
        } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
          console.warn('Realtime connection issue:', status);
        }
      });

    subscriptionRef.current = channel;

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  // Filter & Paginate
  const filteredFeedback = useMemo(() => {
    if (filterRating === 'all') return feedback;
    return feedback.filter(f => f.rating === parseInt(filterRating));
  }, [feedback, filterRating]);

  const paginatedFeedback = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredFeedback.slice(start, start + itemsPerPage);
  }, [filteredFeedback, currentPage]);

  const totalPages = Math.ceil(filteredFeedback.length / itemsPerPage);

  useEffect(() => {
    setCurrentPage(1);
  }, [filterRating]);

  // Calculate average
  const avgRating =
    feedback.length > 0
      ? feedback.reduce((sum, f) => sum + f.rating, 0) / feedback.length
      : 0;

  const totalReviews = feedback.length;

  return (
    <>
      {/* === PAGE TITLE + ICON === */}
      <Helmet>
        <title>PDF Merger Pro - User Reviews & Ratings</title>
        <link
          rel="icon"
          href="https://cdn-icons-png.flaticon.com/512/337/337946.png"
          type="image/png"
        />
        <link
          rel="apple-touch-icon"
          href="https://cdn-icons-png.flaticon.com/512/337/337946.png"
        />
        <meta name="description" content="Real-time user feedback for PDF Merger Pro - merge PDFs fast and easy." />
      </Helmet>

      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4 md:py-12">
        <div className="max-w-7xl mx-auto">

          {/* Header */}
          <div className="text-center mb-8 md:mb-12">
            <div className="flex justify-center items-center gap-3">
              <img
                src="https://cdn-icons-png.flaticon.com/512/337/337946.png"
                alt="PDF Icon"
                className="w-10 h-10 md:w-12 md:h-12"
              />
              <h1 className="text-3xl md:text-5xl font-bold text-gray-800">PDF Merger Pro</h1>
            </div>
            <p className="text-base md:text-xl text-gray-600 mt-2">User Feedback & Ratings</p>
            <div className="flex justify-center items-center mt-3 gap-3">
              {/* Live Updates Badge */}
              <div className="flex items-center gap-2">
                <div className="relative">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <div className="absolute inset-0 w-2 h-2 bg-green-500 rounded-full animate-ping"></div>
                </div>
                <span className="text-xs font-medium text-green-700 bg-green-100 px-3 py-1 rounded-full">
                  Live Updates
                </span>
              </div>

              {/* Manila Clock */}
              <ManilaClock />
            </div>
          </div>

          {/* Summary Card */}
          <div className="bg-white rounded-2xl shadow-xl p-6 md:p-10 mb-8 md:mb-12 text-center max-w-md mx-auto">
            <div className="flex flex-col md:flex-row justify-center items-center space-y-4 md:space-y-0 md:space-x-6">
              <div className="text-5xl md:text-7xl font-bold text-indigo-600">
                {avgRating.toFixed(1)}
              </div>
              <div>
                <div className="flex justify-center mb-2">
                  <StarRating rating={Math.round(avgRating)} />
                </div>
                <p className="text-sm md:text-base text-gray-500">
                  {totalReviews} review{totalReviews !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
          </div>

          {/* Filter & Controls */}
          <div className="flex flex-col md:flex-row justify-between items-center mb-6 space-y-4 md:space-y-0">
            <div className="flex items-center space-x-3">
              <img
                src="https://cdn-icons-png.flaticon.com/512/61/61456.png"
                alt="Filter"
                className="w-5 h-5 text-gray-600"
              />
              <label htmlFor="rating-filter" className="text-sm font-medium text-gray-700">
                Filter by stars:
              </label>
              <select
                id="rating-filter"
                value={filterRating}
                onChange={(e) => setFilterRating(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
              >
                <option value="all">All Ratings</option>
                {[5, 4, 3, 2, 1].map(n => (
                  <option key={n} value={n}>{n} Star{n !== 1 ? 's' : ''}</option>
                ))}
              </select>
            </div>

            <p className="text-sm text-gray-600">
              Showing {paginatedFeedback.length} of {filteredFeedback.length} review{filteredFeedback.length !== 1 ? 's' : ''}
            </p>
          </div>

          {/* Loading / Error */}
          {loading && (
            <div className="text-center py-16">
              <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-indigo-600 border-t-transparent"></div>
              <p className="text-gray-600 mt-4">Loading feedback...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-xl mb-8 text-center">
              {error}
            </div>
          )}

          {/* Feedback Grid */}
          {!loading && !error && filteredFeedback.length === 0 && (
            <div className="text-center py-20 text-gray-500">
              <img
                src="https://cdn-icons-png.flaticon.com/512/748/748113.png"
                alt="No feedback"
                className="w-16 h-16 mx-auto mb-4 opacity-50"
              />
              <p className="text-lg">No feedback yet. Waiting.</p>
            </div>
          )}

          {!loading && !error && filteredFeedback.length > 0 && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 auto-rows-fr">
                {paginatedFeedback.map((item) => (
                  <div
                    key={item.id}
                    className="bg-white rounded-xl shadow-md p-5 hover:shadow-xl transition-all duration-300 flex flex-col h-full border border-gray-100"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <img
                            src="https://cdn-icons-png.flaticon.com/512/64/64572.png"
                            alt="User"
                            className="w-5 h-5 text-gray-500"
                          />
                          <p className="font-semibold text-gray-800 truncate">
                            {item.name || 'Anonymous'}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
                          <img
                            src="https://cdn-icons-png.flaticon.com/512/54/54158.png"
                            alt="Time"
                            className="w-3 h-3"
                          />
                          {formatManilaTime(item.created_at)}
                        </div>
                      </div>
                      <StarRating rating={item.rating} />
                    </div>
                    <p className="text-gray-700 text-sm leading-relaxed flex-1 overflow-hidden">
                      {item.comment}
                    </p>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center items-center mt-10 space-x-2">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-1 ${currentPage === 1
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-white text-gray-700 hover:bg-gray-100 shadow-md'
                      }`}
                  >
                    Previous
                  </button>

                  <div className="flex space-x-1">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`w-10 h-10 rounded-lg font-medium transition-colors ${currentPage === page
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white text-gray-700 hover:bg-gray-100 shadow-md'
                          }`}
                      >
                        {page}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-1 ${currentPage === totalPages
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-white text-gray-700 hover:bg-gray-100 shadow-md'
                      }`}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}

          {/* Footer */}
          <footer className="mt-16 text-center text-xs text-gray-500 flex items-center justify-center gap-2">
            <img
              src={supabaseLogo}
              alt="Supabase"
              className="w-auto h-6"
            />
            Feedback powered by Supabase • Times in GMT+8 (Manila) • Live Updates
          </footer>
        </div>
      </div>
    </>
  );
}