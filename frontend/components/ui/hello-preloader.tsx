"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { AppleHelloEnglishEffect } from "@/components/ui/apple-hello";

export interface HelloPreloaderProps {
  onComplete?: () => void;
  speed?: number;
}

export function HelloPreloader({ onComplete, speed = 0.9 }: HelloPreloaderProps) {
  const [visible, setVisible] = useState<boolean>(true);

  const handleDone = () => {
    // Graceful delay before fading out
    setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, 400);
  };

  useEffect(() => {
    // Safety fallback: maximum 4 seconds in case animation event does not fire
    const fallbackTimer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, 4200);

    return () => clearTimeout(fallbackTimer);
  }, [onComplete]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="hello-preloader"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.8, ease: "easeInOut" } }}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#080c14] select-none"
        >
          {/* Subtle background glow */}
          <div className="absolute h-72 w-72 rounded-full bg-blue-500/10 blur-[100px] pointer-events-none" />

          {/* Apple Hello Animated Stroke */}
          <div className="relative z-10 flex flex-col items-center">
            <AppleHelloEnglishEffect
              className="text-slate-100 h-24 sm:h-28 drop-shadow-[0_0_20px_rgba(255,255,255,0.2)]"
              speed={speed}
              onAnimationComplete={handleDone}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default HelloPreloader;
