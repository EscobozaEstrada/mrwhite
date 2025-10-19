import React from 'react';

const Rotating3DCard = () => {
  return (
    <div className="bg-transparent flex items-center justify-center p-4 md:p-8">
      <div className="perspective-1000">
        <div className="card-container">
          {/* Card Front */}
          <div className="card-face card-front">
            <img
              src="/assets/pass-front.png" 
              alt="Front Card Image"
              className="w-full h-full object-cover rounded-2xl"
            />
          </div>

          {/* Card Back */}
          <div className="card-face card-back">
            <img
              src="/assets/pass-back.png"
              alt="Back Card Image"
              className="w-full h-full object-cover rounded-2xl"
            />
          </div>
        </div>
      </div>

      <style jsx>{`
        .perspective-1000 {
          perspective: 1200px;
          perspective-origin: center center;
        }
        
        .card-container {
          position: relative;
          width: 280px;
          height: 175px;
          transform-style: preserve-3d;
          animation: rotateCard 8s linear infinite;
          transform: rotateX(-15deg) rotateY(-10deg);
        }
        
        @media (min-width: 640px) {
          .card-container {
            width: 320px;
            height: 200px;
          }
        }
        
        @media (min-width: 768px) {
          .card-container {
            width: 400px;
            height: 250px;
          }
        }
        
        .card-face {
          position: absolute;
          width: 100%;
          height: 100%;
          backface-visibility: hidden;
          border-radius: 20px;
          overflow: hidden;
          box-shadow: 
            0 0 30px rgba(0, 0, 0, 0.5),
            0 10px 20px rgba(0, 0, 0, 0.3);
        }
        
        .card-front {
          transform: rotateY(0deg);
        }
        
        .card-back {
          transform: rotateY(180deg);
        }
        
        @keyframes rotateCard {
          0% {
            transform: rotateX(-15deg) rotateY(-10deg);
          }
          25% {
            transform: rotateX(-10deg) rotateY(80deg);
          }
          50% {
            transform: rotateX(-15deg) rotateY(170deg);
          }
          75% {
            transform: rotateX(-20deg) rotateY(260deg);
          }
          100% {
            transform: rotateX(-15deg) rotateY(350deg);
          }
        }
        
        /* Add floating animation */
        .card-container::before {
          content: '';
          position: absolute;
          top: -10px;
          left: -10px;
          right: -10px;
          bottom: -10px;
          background: radial-gradient(circle at center, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
          border-radius: 30px;
          z-index: -1;
          animation: pulse 2s ease-in-out infinite alternate;
        }
        
        @keyframes pulse {
          0% {
            transform: scale(1);
            opacity: 0.3;
          }
          100% {
            transform: scale(1.05);
            opacity: 0.6;
          }
        }
      `}</style>
    </div>
  );
};

export default Rotating3DCard;
