import { useLayoutEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import { Activity, Check, MapPin, Route, Truck } from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const STEPS = [
  {
    label: "01 / PLAN",
    title: "Plan with context.",
    description: "Bring stops, fleet capacity and working windows together before dispatch.",
    icon: Route,
  },
  {
    label: "02 / MOVE",
    title: "Follow every move.",
    description: "Coordinate routes, drivers and deliveries from one shared operational view.",
    icon: Truck,
  },
  {
    label: "03 / COMPLETE",
    title: "Close the delivery loop.",
    description: "Keep customer updates and proof of delivery connected to every shipment.",
    icon: Check,
  },
];

const PANELS = [
  { eyebrow: "DISPATCH", title: "Route ready", detail: "Stops organized for the day", icon: Route },
  { eyebrow: "IN TRANSIT", title: "Vehicle en route", detail: "Route progress in one view", icon: Activity },
  { eyebrow: "DELIVERY", title: "Delivery complete", detail: "Proof linked to the shipment", icon: Check },
];

export function Showcase() {
  const root = useRef<HTMLElement>(null);
  const steps = useRef<HTMLDivElement>(null);
  const route = useRef<SVGPathElement>(null);
  const vehicle = useRef<SVGGElement>(null);
  const reduceMotion = useReducedMotion();

  useLayoutEffect(() => {
    if (reduceMotion || !root.current || !steps.current || !route.current || !vehicle.current) return;
    const path = route.current;
    const van = vehicle.current;
    const pathLength = path.getTotalLength();
    const markers = Array.from(root.current.querySelectorAll<SVGCircleElement>("[data-story-marker]"));
    const panels = Array.from(root.current.querySelectorAll<HTMLElement>("[data-story-panel]"));
    const stepCards = Array.from(root.current.querySelectorAll<HTMLElement>("[data-story-step]"));

    const context = gsap.context(() => {
      gsap.set(path, { strokeDasharray: pathLength, strokeDashoffset: pathLength });
      gsap.set(van, { attr: { transform: "translate(90 500)" } });
      gsap.set(markers, { scale: 0.65, transformOrigin: "center center", opacity: 0.4 });
      gsap.set(panels, { autoAlpha: 0, y: 10 });
      gsap.set(panels[0], { autoAlpha: 1, y: 0 });

      ScrollTrigger.create({
        trigger: steps.current,
        start: "top 68%",
        end: "bottom 68%",
        scrub: 0.7,
        onUpdate: ({ progress }) => {
          const point = path.getPointAtLength(pathLength * progress);
          gsap.set(path, { strokeDashoffset: pathLength * (1 - progress) });
          gsap.set(van, { attr: { transform: `translate(${point.x} ${point.y})` } });

          markers.forEach((marker, index) => {
            const reached = progress >= [0.02, 0.45, 0.94][index];
            gsap.set(marker, { scale: reached ? 1 : 0.65, opacity: reached ? 1 : 0.4 });
          });

          panels.forEach((panel, index) => {
            const center = [0.14, 0.5, 0.86][index];
            const strength = Math.max(0, 1 - Math.abs(progress - center) / 0.3);
            gsap.set(panel, { autoAlpha: strength, y: 10 * (1 - strength) });
          });

          stepCards.forEach((card, index) => {
            const center = (index + 0.5) / stepCards.length;
            const strength = Math.max(0, 1 - Math.abs(progress - center) * 2.8);
            card.style.opacity = String(0.58 + strength * 0.42);
            card.style.transform = `translateY(${(1 - strength) * 5}px)`;
          });
        },
      });
    }, root);

    return () => context.revert();
  }, [reduceMotion]);

  return (
    <section ref={root} id="showcase" className="mx-auto max-w-6xl px-4 py-16 md:py-24">
      <div data-reveal className="mb-10 max-w-2xl">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-electric">Illustrative workflow</p>
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">One view. Every move.</h2>
        <p className="mt-3 max-w-xl leading-7 text-muted">Scroll through a delivery day and see how planning, movement and proof connect.</p>
      </div>

      <div className="grid items-start gap-8 lg:grid-cols-[0.82fr_1.18fr] lg:gap-12">
        <div className="glass sticky top-20 order-first self-start overflow-hidden rounded-3xl border-electric/20 p-0 shadow-[0_24px_100px_rgb(0_0_0/0.4)] lg:order-last">
          <div className="relative h-[22rem] overflow-hidden sm:h-[26rem] lg:h-[min(68vh,36rem)] lg:min-h-[32rem]">
            <div className="absolute inset-0 bg-[#070a13]" />
            <div className="absolute inset-0 opacity-25 [background-image:linear-gradient(rgb(110_130_180/0.16)_1px,transparent_1px),linear-gradient(90deg,rgb(110_130_180/0.16)_1px,transparent_1px)] [background-size:42px_42px]" />
            <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-electric/10 blur-3xl" />
            <div className="absolute -bottom-24 -right-10 h-72 w-72 rounded-full bg-violet/10 blur-3xl" />

            <svg viewBox="0 0 1000 600" className="absolute inset-0 h-full w-full" role="img" aria-label="Illustration of a delivery vehicle moving along a planned route">
              <g fill="none" stroke="rgb(116 132 170 / 0.13)" strokeWidth="18" strokeLinecap="round">
                <path d="M-20 150 C180 180 230 80 420 150 S760 120 1020 175" />
                <path d="M-40 370 C160 310 250 420 440 380 S740 460 1040 360" />
                <path d="M180 -30 C220 120 160 260 220 640" />
                <path d="M480 -40 C420 100 540 240 480 640" />
                <path d="M790 -30 C730 160 850 300 790 640" />
              </g>
              <g fill="none" stroke="rgb(116 132 170 / 0.28)" strokeWidth="2" strokeDasharray="8 12">
                <path d="M-20 150 C180 180 230 80 420 150 S760 120 1020 175" />
                <path d="M-40 370 C160 310 250 420 440 380 S740 460 1040 360" />
                <path d="M180 -30 C220 120 160 260 220 640" />
                <path d="M480 -40 C420 100 540 240 480 640" />
                <path d="M790 -30 C730 160 850 300 790 640" />
              </g>
              <path d="M90 500 C180 400 230 460 300 390 C360 330 410 370 470 320 C540 260 575 300 635 245 C700 180 780 260 910 105"
                fill="none" stroke="rgb(77 141 255 / 0.22)" strokeWidth="26" strokeLinecap="round" />
              <path
                ref={route}
                d="M90 500 C180 400 230 460 300 390 C360 330 410 370 470 320 C540 260 575 300 635 245 C700 180 780 260 910 105"
                fill="none" stroke="url(#fleetmind-route-gradient)" strokeWidth="8" strokeLinecap="round"
              />
              <defs>
                <linearGradient id="fleetmind-route-gradient" x1="0" x2="1" y1="1" y2="0">
                  <stop offset="0%" stopColor="#4d8dff" />
                  <stop offset="100%" stopColor="#9b6bff" />
                </linearGradient>
              </defs>
              <g fill="#0b1020" stroke="#78a8ff" strokeWidth="5">
                <circle data-story-marker cx="90" cy="500" r="13" />
                <circle data-story-marker cx="470" cy="320" r="13" />
                <circle data-story-marker cx="910" cy="105" r="13" />
              </g>
              <g ref={vehicle} transform="translate(90 500)">
                <circle r="28" fill="rgb(77 141 255 / 0.22)" />
                <circle r="19" fill="#4d8dff" stroke="#dbe8ff" strokeWidth="2" />
                <path d="M-12 -7h12v13h-12z M0 -3h7l5 5v4H0z" fill="#fff" stroke="#0c1631" strokeWidth="2" strokeLinejoin="round" />
                <circle cx="-7" cy="8" r="2" fill="#0c1631" />
                <circle cx="7" cy="8" r="2" fill="#0c1631" />
              </g>
            </svg>

            <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full border border-white/10 bg-black/45 px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.14em] text-white/75 backdrop-blur-md">
              <span className="h-1.5 w-1.5 rounded-full bg-electric shadow-[0_0_12px_#4d8dff]" />
              Fleet route preview
            </div>
            <div className="absolute bottom-4 left-4 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-white/50">
              <MapPin size={12} /> Depot <span className="mx-1 text-white/25">/</span> Stops <span className="mx-1 text-white/25">/</span> Destination
            </div>
            {PANELS.map(({ eyebrow, title, detail, icon: Icon }, index) => (
              <div
                key={eyebrow}
                data-story-panel
                className={`absolute right-4 top-16 w-52 rounded-2xl border border-white/10 bg-[#0b1020]/90 p-3.5 text-white shadow-2xl backdrop-blur-xl sm:right-6 sm:top-20 sm:w-60 ${index ? "invisible" : ""}`}
              >
                <div className="flex items-start gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-electric/15 text-electric"><Icon size={17} /></span>
                  <span>
                    <span className="block text-[9px] font-semibold tracking-[0.16em] text-electric">{eyebrow}</span>
                    <span className="mt-1 block text-sm font-semibold">{title}</span>
                    <span className="mt-1 block text-[11px] leading-4 text-white/55">{detail}</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div ref={steps} className="space-y-5 lg:py-[8vh]">
          {STEPS.map(({ label, title, description, icon: Icon }, index) => (
            <article
              key={label}
              data-story-step
              className="min-h-[30vh] rounded-2xl border border-line/70 bg-surface/35 p-5 backdrop-blur-sm sm:p-7 lg:min-h-[38vh]"
            >
              <div className="flex items-center justify-between gap-4">
                <span className="text-[11px] font-semibold tracking-[0.18em] text-electric">{label}</span>
                <span className="grid h-10 w-10 place-items-center rounded-xl border border-electric/20 bg-electric/10 text-electric"><Icon size={18} /></span>
              </div>
              <h3 className="mt-8 text-2xl font-bold tracking-tight sm:text-3xl">{title}</h3>
              <p className="mt-3 max-w-sm leading-7 text-muted">{description}</p>
              <div className="mt-8 flex items-center gap-2 text-xs text-muted">
                <span className={`h-1.5 w-1.5 rounded-full ${index === 2 ? "bg-ok" : "bg-electric"}`} />
                {index === 0 ? "Before dispatch" : index === 1 ? "During the journey" : "At the destination"}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
