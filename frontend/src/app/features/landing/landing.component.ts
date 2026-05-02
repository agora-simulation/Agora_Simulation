import {
  Component, AfterViewInit, OnDestroy, ElementRef, viewChild, signal,
  ChangeDetectionStrategy, NgZone, inject, HostListener,
} from '@angular/core';
import { RouterLink } from '@angular/router';

interface Dot { x: number; y: number; vx: number; vy: number; r: number; pulse: number; }

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent implements AfterViewInit, OnDestroy {
  private zone = inject(NgZone);

  canvas = viewChild<ElementRef<HTMLCanvasElement>>('heroCanvas');
  heroSection = viewChild<ElementRef<HTMLElement>>('heroEl');

  private ctx!: CanvasRenderingContext2D;
  private dots: Dot[] = [];
  private raf = 0;
  private resizeObs?: ResizeObserver;
  private io?: IntersectionObserver;
  private mouseX = 0.5;
  private mouseY = 0.5;

  /* Counters */
  counterPersonas = signal(0);
  counterDays = signal(0);
  counterEvents = signal(0);
  private countersStarted = false;

  /* Title animation */
  titleReady = signal(false);

  /* Typewriter */
  typedText = signal('');
  readonly fullText = 'Marktforschung ohne eine einzige echte Befragung.';
  private typeTimer: any;

  /* Tilt cards */
  tiltStyles: Record<string, string> = {};

  /* Magnetic CTA */
  ctaMagnetX = signal(0);
  ctaMagnetY = signal(0);

  /* ---- Mouse tracking for hero gradient ---- */
  @HostListener('mousemove', ['$event'])
  onMouseMove(e: MouseEvent) {
    const w = window.innerWidth, h = window.innerHeight;
    this.mouseX = e.clientX / w;
    this.mouseY = e.clientY / h;

    // Update hero gradient via CSS custom property
    const hero = this.heroSection()?.nativeElement;
    if (hero) {
      hero.style.setProperty('--mx', `${e.clientX}px`);
      hero.style.setProperty('--my', `${e.clientY}px`);
    }
  }

  /* ---- Lifecycle ---- */

  ngAfterViewInit() {
    this.zone.runOutsideAngular(() => {
      this.initCanvas();
    });
    this.initScrollReveal();
    // Trigger title animation after short delay
    setTimeout(() => this.titleReady.set(true), 300);
    // Start typewriter
    this.startTypewriter();
  }

  ngOnDestroy() {
    cancelAnimationFrame(this.raf);
    this.resizeObs?.disconnect();
    this.io?.disconnect();
    clearTimeout(this.typeTimer);
  }

  /* ---- Typewriter ---- */
  private startTypewriter() {
    let i = 0;
    const type = () => {
      if (i <= this.fullText.length) {
        this.typedText.set(this.fullText.slice(0, i));
        i++;
        this.typeTimer = setTimeout(type, 35 + Math.random() * 25);
      }
    };
    // Delay start until hero is visible
    setTimeout(type, 1800);
  }

  /* ---- 3D Tilt ---- */
  onCardMouseMove(event: MouseEvent, cardId: string) {
    const el = event.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    const rotateX = (y - 0.5) * -12;
    const rotateY = (x - 0.5) * 12;
    el.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
    el.style.setProperty('--shine-x', `${x * 100}%`);
    el.style.setProperty('--shine-y', `${y * 100}%`);
  }

  onCardMouseLeave(event: MouseEvent) {
    const el = event.currentTarget as HTMLElement;
    el.style.transform = 'perspective(800px) rotateX(0) rotateY(0) scale(1)';
  }

  /* ---- Magnetic CTA ---- */
  onCtaMouseMove(event: MouseEvent) {
    const el = event.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    this.ctaMagnetX.set((event.clientX - cx) * 0.2);
    this.ctaMagnetY.set((event.clientY - cy) * 0.2);
  }

  onCtaMouseLeave() {
    this.ctaMagnetX.set(0);
    this.ctaMagnetY.set(0);
  }

  /* ---- Canvas constellation ---- */

  private initCanvas() {
    const el = this.canvas()?.nativeElement;
    if (!el) return;
    this.ctx = el.getContext('2d')!;

    const resize = () => {
      const dpr = devicePixelRatio;
      const rect = el.parentElement!.getBoundingClientRect();
      el.width = rect.width * dpr;
      el.height = rect.height * dpr;
      el.style.width = rect.width + 'px';
      el.style.height = rect.height + 'px';
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      this.seedDots(rect.width, rect.height);
    };
    resize();
    this.resizeObs = new ResizeObserver(resize);
    this.resizeObs.observe(el.parentElement!);
    this.tick();
  }

  private seedDots(w: number, h: number) {
    const count = Math.min(120, Math.floor((w * h) / 8000));
    this.dots = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      r: Math.random() * 2.5 + 0.8,
      pulse: Math.random() * Math.PI * 2,
    }));
  }

  private tick = () => {
    const el = this.canvas()?.nativeElement;
    if (!el) return;
    const w = el.width / devicePixelRatio;
    const h = el.height / devicePixelRatio;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, w, h);

    const now = performance.now() * 0.001;
    const mxWorld = this.mouseX * w;
    const myWorld = this.mouseY * h;

    for (const d of this.dots) {
      // Subtle attraction toward mouse
      const dmx = mxWorld - d.x, dmy = myWorld - d.y;
      const dmDist = Math.sqrt(dmx * dmx + dmy * dmy);
      if (dmDist < 250 && dmDist > 1) {
        d.vx += (dmx / dmDist) * 0.008;
        d.vy += (dmy / dmDist) * 0.008;
      }

      // Damping
      d.vx *= 0.998;
      d.vy *= 0.998;

      d.x += d.vx;
      d.y += d.vy;
      if (d.x < 0 || d.x > w) d.vx *= -1;
      if (d.y < 0 || d.y > h) d.vy *= -1;
    }

    // Edges
    const maxDist = 130;
    for (let i = 0; i < this.dots.length; i++) {
      for (let j = i + 1; j < this.dots.length; j++) {
        const a = this.dots[i], b = this.dots[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < maxDist) {
          const alpha = (1 - dist / maxDist) * 0.15;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(42, 108, 184, ${alpha})`;
          ctx.lineWidth = 0.7;
          ctx.stroke();
        }
      }
    }

    // Dots with pulse
    for (const d of this.dots) {
      const pulseFactor = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(now * 1.5 + d.pulse));
      const r = d.r * pulseFactor + d.r * 0.5;

      // Outer glow
      const grad = ctx.createRadialGradient(d.x, d.y, 0, d.x, d.y, r * 4);
      grad.addColorStop(0, `rgba(42, 108, 184, ${0.12 * pulseFactor})`);
      grad.addColorStop(1, 'rgba(42, 108, 184, 0)');
      ctx.beginPath();
      ctx.arc(d.x, d.y, r * 4, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();

      // Core
      ctx.beginPath();
      ctx.arc(d.x, d.y, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(42, 108, 184, ${0.35 + 0.25 * pulseFactor})`;
      ctx.fill();
    }

    this.raf = requestAnimationFrame(this.tick);
  };

  /* ---- Scroll reveal ---- */

  private initScrollReveal() {
    this.io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).classList.add('revealed');
            if ((entry.target as HTMLElement).classList.contains('stats-trigger') && !this.countersStarted) {
              this.countersStarted = true;
              this.animateCounter('personas', 500, 2400);
              this.animateCounter('days', 60, 2000);
              this.animateCounter('events', 10000, 2800);
            }
            this.io?.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12 },
    );
    setTimeout(() => {
      document.querySelectorAll('.reveal').forEach((el) => this.io?.observe(el));
    }, 50);
  }

  private animateCounter(name: 'personas' | 'days' | 'events', target: number, duration: number) {
    const start = performance.now();
    const step = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 4);
      const val = Math.round(eased * target);
      if (name === 'personas') this.counterPersonas.set(val);
      if (name === 'days') this.counterDays.set(val);
      if (name === 'events') this.counterEvents.set(val);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
}
