"use client";

import React, { useState, useRef, useEffect, useLayoutEffect } from "react";
import { motion } from "framer-motion";

export interface FocusSliceItem {
  id?: string | number;
  image?: string;
  tint?: string;
  kicker: string;
  title: string;
  subtitle?: string;
  action?: string;
  href?: string;
  newTab?: boolean;
  onAction?: (item: FocusSliceItem) => void;
  badge?: {
    label: string;
    color?: string;
  };
  isActive?: boolean;
  metadata?: Record<string, any>;
}

export interface FocusSliceCarouselProps {
  items: FocusSliceItem[];
  canvas?: string;
  ink?: string;
  muted?: string;
  link?: string;
  padding?: number;
  gap?: number;
  radius?: number;
  focusRatio?: number;
  duration?: number;
  panelHeight?: number;
  panelColor?: string;
  panelOpacity?: number;
  panelBlur?: number;
  selectedIndex?: number;
  onSelectIndex?: (index: number) => void;
  className?: string;
  style?: React.CSSProperties;
}

const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;

/**
 * FOCUS SLICE CAROUSEL (LineupGallery)
 * Apple-style full-bleed cards with interactive slice expansion.
 * Opening a card smoothly slides up an info panel while neighbors make room.
 * Easing: cubic-bezier(0.32, 0.72, 0, 1).
 */
export default function FocusSliceCarousel({
  items = [],
  canvas = "#0e1422",
  ink = "#f1f5f9",
  muted = "#94a3b8",
  link = "#3b82f6",
  padding = 16,
  gap = 12,
  radius = 20,
  focusRatio = 3.6,
  duration = 0.62,
  panelHeight = 44,
  panelColor = "#080c14",
  panelOpacity = 94,
  panelBlur = 12,
  selectedIndex,
  onSelectIndex,
  className = "",
  style,
}: FocusSliceCarouselProps) {
  const [open, setOpen] = useState<number>(selectedIndex ?? 0);
  const [hovered, setHovered] = useState<number>(-1);
  const [failedImages, setFailedImages] = useState<Record<number, boolean>>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1100);

  // Sync external selectedIndex if supplied
  useEffect(() => {
    if (selectedIndex !== undefined) {
      setOpen(selectedIndex);
    }
  }, [selectedIndex]);

  useIsomorphicLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setWidth(entry.contentRect.width);
    });
    ro.observe(el);
    setWidth(el.getBoundingClientRect().width);
    return () => ro.disconnect();
  }, []);

  // Apple's characteristic web easing curve
  const ease = { duration, ease: [0.32, 0.72, 0, 1] as const };

  const count = Math.max(items.length, 1);
  const track = Math.max(width - padding * 2 - gap * (count - 1), 0);
  const openWidth =
    open === -1 ? track / count : (track * focusRatio) / (focusRatio + count - 1);

  const handleCardClick = (index: number) => {
    setOpen(index);
    onSelectIndex?.(index);
  };

  const handleClose = (e: React.MouseEvent) => {
    e.stopPropagation();
    setOpen(-1);
    onSelectIndex?.(-1);
  };

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        width: "100%",
        height: "100%",
        minWidth: 320,
        minHeight: 340,
        background: canvas,
        borderRadius: radius + padding / 2,
        padding,
        boxSizing: "border-box",
        overflow: "hidden",
        ...style,
      }}
    >
      <div
        style={{
          display: "flex",
          gap,
          width: "100%",
          height: "100%",
        }}
      >
        {items.map((item, i) => {
          const isOpen = i === open;
          const isHovered = i === hovered && !isOpen;
          const isItemActive = item.isActive;

          return (
            <motion.div
              key={item.id ?? item.title ?? i}
              onClick={() => handleCardClick(i)}
              onHoverStart={() => setHovered(i)}
              onHoverEnd={() => setHovered(-1)}
              initial={false}
              animate={{
                flexGrow: isOpen ? focusRatio : 1,
              }}
              transition={ease}
              style={{
                position: "relative",
                flexBasis: 0,
                minWidth: 0,
                height: "100%",
                borderRadius: radius,
                overflow: "hidden",
                maskImage: "-webkit-radial-gradient(white, black)",
                WebkitMaskImage: "-webkit-radial-gradient(white, black)",
                isolation: "isolate",
                cursor: isOpen ? "default" : "pointer",
                background: item.tint ?? "#162032",
                willChange: "flex-grow",
                transform: "translateZ(0)",
                border: isItemActive
                  ? "2px solid #f59e0b"
                  : "1px solid rgba(255,255,255,0.08)",
                boxShadow: isItemActive
                  ? "0 0 20px rgba(245, 158, 11, 0.25)"
                  : "none",
              }}
            >
              {/* Background Art / Imagery */}
              {item.image && (
                <motion.img
                  src={item.image}
                  alt={item.title ?? ""}
                  draggable={false}
                  referrerPolicy="no-referrer"
                  onError={() =>
                    setFailedImages((prev) => ({ ...prev, [i]: true }))
                  }
                  initial={false}
                  animate={{ scale: isOpen ? 1 : isHovered ? 1.04 : 1.08 }}
                  transition={ease}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: "50%",
                    x: "-50%",
                    height: "100%",
                    width: width,
                    objectFit: "cover",
                    userSelect: "none",
                    opacity: failedImages[i] ? 0 : 0.85,
                    willChange: "transform",
                  }}
                />
              )}

              {/* Tint / Vignette gradient */}
              <motion.div
                initial={false}
                animate={{ opacity: isOpen ? 0.35 : 0.7 }}
                transition={ease}
                style={{
                  position: "absolute",
                  inset: 0,
                  background:
                    "linear-gradient(to top, rgba(8,12,20,0.85) 0%, rgba(8,12,20,0.3) 50%, rgba(8,12,20,0.6) 100%)",
                  pointerEvents: "none",
                }}
              />

              {/* Vertical Title on Closed Card - Fully Visible & Centered */}
              <motion.div
                initial={false}
                animate={{ opacity: isOpen ? 0 : 1 }}
                transition={ease}
                style={{
                  position: "absolute",
                  top: 20,
                  bottom: 56,
                  left: 0,
                  right: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  pointerEvents: "none",
                  zIndex: 3,
                }}
              >
                <span
                  style={{
                    writingMode: "vertical-rl",
                    transform: "rotate(180deg)",
                    fontSize:
                      item.title.length > 40
                        ? 11
                        : item.title.length > 30
                        ? 11.5
                        : 12.5,
                    fontWeight: 600,
                    letterSpacing:
                      item.title.length > 40 ? "-0.01em" : "0.01em",
                    color: "#f8fafc",
                    textShadow:
                      "0 2px 12px rgba(0,0,0,0.95), 0 0 6px rgba(0,0,0,0.9)",
                    whiteSpace: "nowrap",
                    textAlign: "center",
                    maxHeight: "100%",
                  }}
                >
                  {item.title}
                </span>
              </motion.div>

              {/* Slide-Up Bottom Info Panel */}
              <motion.div
                initial={false}
                animate={{ y: isOpen ? "0%" : "101%" }}
                transition={ease}
                style={{
                  position: "absolute",
                  left: -1,
                  right: -1,
                  bottom: -1,
                  height: `calc(${panelHeight}% + 1px)`,
                  borderBottomLeftRadius: radius + 1,
                  borderBottomRightRadius: radius + 1,
                  padding: "20px 24px",
                  boxSizing: "border-box",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  overflow: "hidden",
                  pointerEvents: isOpen ? "auto" : "none",
                  willChange: "transform",
                }}
              >
                {/* Frosted glass backdrop */}
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: panelColor,
                    opacity: panelOpacity / 100,
                    backdropFilter: panelBlur
                      ? `blur(${panelBlur}px) saturate(1.8)`
                      : undefined,
                    WebkitBackdropFilter: panelBlur
                      ? `blur(${panelBlur}px) saturate(1.8)`
                      : undefined,
                    borderTop: "1px solid rgba(255,255,255,0.1)",
                    borderBottomLeftRadius: radius + 1,
                    borderBottomRightRadius: radius + 1,
                  }}
                />

                {/* Content pinned to openWidth to avoid layout shifts */}
                <div
                  style={{
                    position: "relative",
                    width: openWidth ? openWidth - 48 : "100%",
                    flexShrink: 0,
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                        color: muted,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {item.kicker}
                    </span>
                  </div>

                  <div
                    style={{
                      marginTop: 4,
                      fontSize: 20,
                      lineHeight: 1.2,
                      fontWeight: 700,
                      letterSpacing: "-0.02em",
                      color: ink,
                      whiteSpace: "normal",
                    }}
                  >
                    {item.title}
                  </div>

                  {item.subtitle && (
                    <div
                      style={{
                        marginTop: 6,
                        fontSize: 13,
                        lineHeight: 1.45,
                        color: muted,
                        maxWidth: 600,
                        display: "-webkit-box",
                        WebkitLineClamp: 3,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}
                    >
                      {item.subtitle}
                    </div>
                  )}

                  {/* Action Button */}
                  <div className="mt-3 flex items-center gap-3">
                    {item.onAction ? (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          item.onAction?.(item);
                        }}
                        className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition ${
                          isItemActive
                            ? "bg-amber-500 text-slate-950 hover:bg-amber-400 font-bold shadow-md shadow-amber-500/20"
                            : "bg-blue-600 text-white hover:bg-blue-500 shadow-md shadow-blue-500/20"
                        }`}
                      >
                        <span>{item.action ?? "Apply Disruption"}</span>
                        <span>›</span>
                      </button>
                    ) : item.href ? (
                      <a
                        href={item.href}
                        target={item.newTab ? "_blank" : undefined}
                        rel={item.newTab ? "noopener noreferrer" : undefined}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          fontSize: 14,
                          color: link,
                          whiteSpace: "nowrap",
                          textDecoration: "none",
                          cursor: "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                          fontWeight: 500,
                        }}
                      >
                        {item.action ?? "Learn more"}
                        <span>›</span>
                      </a>
                    ) : null}
                  </div>
                </div>
              </motion.div>

              {/* Rotating "+" into "×" toggle button */}
              <motion.div
                onClick={handleClose}
                initial={false}
                animate={{ rotate: isOpen ? 45 : 0 }}
                whileHover={{ scale: 1.08 }}
                whileTap={{ scale: 0.92 }}
                transition={ease}
                style={{
                  position: "absolute",
                  right: 16,
                  bottom: 16,
                  width: 34,
                  height: 34,
                  borderRadius: 999,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: isOpen
                    ? "rgba(255,255,255,0.12)"
                    : "rgba(255,255,255,0.92)",
                  boxShadow: isOpen
                    ? "none"
                    : "0 2px 10px rgba(0,0,0,0.35)",
                  cursor: "pointer",
                  zIndex: 2,
                  willChange: "transform",
                }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke={isOpen ? "#f1f5f9" : "#0f172a"}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                >
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </motion.div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
