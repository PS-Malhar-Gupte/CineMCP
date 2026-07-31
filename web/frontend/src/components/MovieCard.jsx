import { motion } from 'framer-motion'
import { Star, Calendar, Film } from 'lucide-react'

export default function MovieCard({ movie }) {
  const {
    title,
    year,
    poster,
    rating,
    genre,
    plot,
    director,
    actors,
    releaseDate
  } = movie

  // TMDb poster URL (if available)
  const posterUrl = poster 
    ? `https://image.tmdb.org/t/p/w500${poster}`
    : null

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden border border-gray-200 dark:border-gray-700"
    >
      <div className="md:flex">
        {/* Poster */}
        {posterUrl ? (
          <div className="md:flex-shrink-0 md:w-48">
            <img
              src={posterUrl}
              alt={`${title} poster`}
              className="h-full w-full object-cover"
              onError={(e) => {
                e.target.style.display = 'none'
                e.target.nextSibling.style.display = 'flex'
              }}
            />
            <div 
              className="hidden h-full w-full bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-800 items-center justify-center"
            >
              <Film className="w-16 h-16 text-gray-400 dark:text-gray-600" />
            </div>
          </div>
        ) : (
          <div className="md:flex-shrink-0 md:w-48 bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center min-h-[280px]">
            <Film className="w-16 h-16 text-gray-400 dark:text-gray-600" />
          </div>
        )}

        {/* Content */}
        <div className="p-6 flex-1">
          {/* Title and Year */}
          <div className="flex items-start justify-between gap-4 mb-3">
            <div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                {title}
              </h3>
              {(year || releaseDate) && (
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <Calendar className="w-4 h-4" />
                  <span>{year || releaseDate}</span>
                </div>
              )}
            </div>
            
            {/* Rating */}
            {rating && (
              <div className="flex items-center gap-1 bg-amber-100 dark:bg-amber-900/30 px-3 py-1 rounded-full">
                <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                <span className="text-sm font-semibold text-amber-700 dark:text-amber-300">
                  {rating}
                </span>
              </div>
            )}
          </div>

          {/* Genre Tags */}
          {genre && (
            <div className="flex flex-wrap gap-2 mb-3">
              {genre.split(',').map((g, index) => (
                <span
                  key={index}
                  className="px-2 py-1 text-xs font-medium bg-primary-100 dark:bg-primary-900/30 
                           text-primary-700 dark:text-primary-300 rounded-full"
                >
                  {g.trim()}
                </span>
              ))}
            </div>
          )}

          {/* Plot */}
          {plot && (
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-4 line-clamp-3">
              {plot}
            </p>
          )}

          {/* Director and Cast */}
          <div className="space-y-2 text-sm">
            {director && (
              <div>
                <span className="font-semibold text-gray-900 dark:text-white">Director: </span>
                <span className="text-gray-600 dark:text-gray-400">{director}</span>
              </div>
            )}
            {actors && (
              <div>
                <span className="font-semibold text-gray-900 dark:text-white">Cast: </span>
                <span className="text-gray-600 dark:text-gray-400">{actors}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
