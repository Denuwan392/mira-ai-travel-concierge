import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { MiraSparkle } from "@/components/site/MiraSparkle";
import { photos } from "@/lib/photos";
import { cn } from "@/lib/utils";

interface AuthSplitLayoutProps {
  children: ReactNode;
  imageSrc?: string;
  imageAlt?: string;
  eyebrow?: string;
  headline?: string;
  subtext?: string;
  cardClassName?: string;
}

export function AuthSplitLayout({
  children,
  imageSrc = photos.sigiriyaAerial.src,
  imageAlt = photos.sigiriyaAerial.alt,
  eyebrow = "CEYLON COMPASS HOLIDAYS",
  headline = "Your next story begins in Sri Lanka.",
  subtext = "Discover remarkable places, thoughtful journeys, and experiences designed around you.",
  cardClassName,
}: AuthSplitLayoutProps) {
  return (
    <div className="min-h-screen flex justify-center items-start pt-[86px] sm:pt-[92px] pb-10 px-4 sm:px-6 lg:px-8 bg-[#F3EEE6]">
      {/* Outer Floating Card Container */}
      <div
        className={cn(
          "w-full max-w-[980px] bg-white rounded-[22px] border border-[#E0D9CE] shadow-[0_20px_50px_-12px_rgba(20,20,20,0.13),0_4px_16px_rgba(20,20,20,0.03)] overflow-hidden flex flex-col md:flex-row",
          cardClassName,
        )}
      >
        {/* Left Visual Storytelling Panel (Desktop / Tablet) */}
        <div className="relative hidden md:flex md:w-[48%] lg:w-[50%] flex-col justify-between p-6 sm:p-8 lg:p-9 overflow-hidden bg-[#111111]">
          {/* Photographic Background */}
          <img
            src={imageSrc}
            alt={imageAlt}
            className="absolute inset-0 w-full h-full object-cover object-center select-none"
            loading="eager"
          />

          {/* Subtle Dark Editorial Multi-stop Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/45 to-black/30 pointer-events-none" />

          {/* Top Brand Badge */}
          <div className="relative z-10 flex items-center justify-between">
            <Link
              to="/"
              className="inline-flex items-center gap-2 group focus:outline-none focus-visible:ring-2 focus-visible:ring-[#F26B1D] rounded-full"
              aria-label="Ceylon Compass Holidays — home"
            >
              <div className="size-8 rounded-full bg-white/15 backdrop-blur-md border border-white/20 flex items-center justify-center group-hover:bg-white/25 transition-colors duration-150">
                <MiraSparkle className="size-3.5 text-[#F26B1D]" />
              </div>
              <span className="flex flex-col text-white">
                <span className="text-[12px] font-bold tracking-[0.16em] uppercase leading-none">Ceylon Compass</span>
                <span className="text-[9.5px] text-white/70 tracking-[0.25em] uppercase font-medium mt-0.5">Holidays</span>
              </span>
            </Link>

            <span className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10.5px] font-medium tracking-wider uppercase bg-white/15 backdrop-blur-md text-white/90 border border-white/20">
              ✦ Curated Travel
            </span>
          </div>

          {/* Bottom Editorial Content */}
          <div className="relative z-10 space-y-3 pt-8">
            <p className="eyebrow text-[10.5px] font-semibold tracking-[0.22em] text-[#F26B1D] uppercase">
              {eyebrow}
            </p>
            <h2 className="text-[25px] sm:text-[28px] lg:text-[30px] font-bold text-white tracking-[-0.03em] leading-[1.15]">
              {headline}
            </h2>
            <p className="text-[13px] text-white/85 leading-relaxed max-w-[380px]">
              {subtext}
            </p>

            {/* Subtle Brand Feature Markers */}
            <div className="pt-1 flex flex-wrap items-center gap-2.5 text-[11.5px] text-white/80 font-normal">
              <span className="inline-flex items-center gap-1.5">
                <span className="size-1.5 rounded-full bg-[#F26B1D]" /> Verified rates
              </span>
              <span className="text-white/30">•</span>
              <span className="inline-flex items-center gap-1.5">
                <span className="size-1.5 rounded-full bg-[#14837B]" /> Private journeys
              </span>
              <span className="text-white/30">•</span>
              <span className="inline-flex items-center gap-1.5">
                <span className="size-1.5 rounded-full bg-[#F5B700]" /> Mira AI Concierge
              </span>
            </div>
          </div>
        </div>

        {/* Mobile Header Visual Banner (<md) */}
        <div className="relative w-full h-[140px] p-4.5 flex flex-col justify-between overflow-hidden md:hidden bg-[#111111]">
          <img
            src={imageSrc}
            alt={imageAlt}
            className="absolute inset-0 w-full h-full object-cover object-center select-none"
            loading="eager"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/35 pointer-events-none" />

          <div className="relative z-10 flex items-center justify-between">
            <Link to="/" className="inline-flex items-center gap-2" aria-label="Ceylon Compass Holidays">
              <MiraSparkle className="size-4 text-[#F26B1D]" />
              <span className="text-[12px] font-bold tracking-[0.16em] uppercase text-white">Ceylon Compass</span>
            </Link>
            <span className="text-[10px] uppercase tracking-wider text-white/80 bg-white/10 px-2 py-0.5 rounded-full border border-white/15">
              Holidays
            </span>
          </div>

          <div className="relative z-10">
            <p className="text-[16px] font-bold text-white tracking-[-0.02em] leading-tight">
              {headline}
            </p>
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="w-full md:w-[52%] lg:w-[50%] flex flex-col justify-center p-6 sm:p-7 lg:p-8 bg-white">
          <div className="w-full max-w-[370px] mx-auto">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
