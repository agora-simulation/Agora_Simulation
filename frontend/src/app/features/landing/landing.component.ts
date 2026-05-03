import {
  Component, AfterViewInit, OnDestroy, ElementRef, viewChild, signal,
  ChangeDetectionStrategy, NgZone, inject, HostListener,
} from '@angular/core';
import { RouterLink } from '@angular/router';

interface NetNode {
  x: number; y: number; vx: number; vy: number;
  radius: number; baseAlpha: number; phase: number;
}
interface Pulse { x: number; y: number; radius: number; maxRadius: number; speed: number; life: number; }
interface Spark { from: NetNode; to: NetNode; t: number; speed: number; }

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
  private nodes: NetNode[] = [];
  private pulses: Pulse[] = [];
  private sparks: Spark[] = [];
  private raf = 0;
  private resizeObs?: ResizeObserver;
  private io?: IntersectionObserver;
  private mouseX = -9999;
  private mouseY = -9999;
  private mouseActive = false;
  private canvasW = 0;
  private canvasH = 0;
  private lastTime = 0;

  /* Network config */
  private readonly net = {
    linkDistance: 150,
    nodeSpeed: 0.18,
    pulseChance: 0.0014,
    sparkChance: 0.0009,
    mouseRadius: 140,
    colors: {
      core:  'rgba(255, 217, 154, ',
      glow:  'rgba(230, 183, 113, ',
      line:  'rgba(184, 118, 58, ',
      pulse: 'rgba(255, 217, 154, ',
      spark: 'rgba(255, 240, 200, ',
    },
  };

  /* Counters */
  counterPersonas = signal(0);
  counterDays = signal(0);
  counterEvents = signal(0);
  private countersStarted = false;

  /* Title animation */
  titleReady = signal(false);

  /* Typewriter */
  typedText = signal('');
  readonly fullText = 'Marktforschung — ohne eine einzige echte Befragung.';
  private typeTimer: any;

  /* Tilt cards */
  tiltStyles: Record<string, string> = {};

  /* Magnetic CTA */
  ctaMagnetX = signal(0);
  ctaMagnetY = signal(0);

  /* ---- Mouse tracking for hero gradient + canvas ---- */
  @HostListener('mousemove', ['$event'])
  onMouseMove(e: MouseEvent) {
    // Update hero gradient via CSS custom property
    const hero = this.heroSection()?.nativeElement;
    if (hero) {
      hero.style.setProperty('--mx', `${e.clientX}px`);
      hero.style.setProperty('--my', `${e.clientY}px`);
    }
    // Update canvas mouse position
    const el = this.canvas()?.nativeElement;
    if (el) {
      const rect = el.getBoundingClientRect();
      this.mouseX = e.clientX - rect.left;
      this.mouseY = e.clientY - rect.top;
      this.mouseActive = true;
    }
  }

  @HostListener('mouseleave')
  onMouseLeave() {
    this.mouseActive = false;
    this.mouseX = -9999;
    this.mouseY = -9999;
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

  /* ---- Network Canvas (Agora Netzwerk-Animation) ---- */

  private initCanvas() {
    const el = this.canvas()?.nativeElement;
    if (!el) return;
    this.ctx = el.getContext('2d')!;
    const dpr = Math.min(devicePixelRatio || 1, 2);

    const resize = () => {
      const rect = el.parentElement!.getBoundingClientRect();
      this.canvasW = rect.width;
      this.canvasH = rect.height;
      el.width = Math.floor(this.canvasW * dpr);
      el.height = Math.floor(this.canvasH * dpr);
      el.style.width = this.canvasW + 'px';
      el.style.height = this.canvasH + 'px';
      this.ctx.setTransform(1, 0, 0, 1, 0, 0);
      this.ctx.scale(dpr, dpr);
      this.seedNodes();
    };
    resize();
    this.resizeObs = new ResizeObserver(resize);
    this.resizeObs.observe(el.parentElement!);

    // Click → pulse
    el.addEventListener('click', (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      this.pulses.push({
        x: e.clientX - rect.left, y: e.clientY - rect.top,
        radius: 0, maxRadius: 70 + Math.random() * 60 * 1.4, speed: 1.1, life: 1,
      });
    });

    this.lastTime = performance.now();
    this.tick();
  }

  private seedNodes() {
    const density = 0.00009;
    const count = Math.max(40, Math.min(130, Math.floor(this.canvasW * this.canvasH * density)));
    this.nodes = Array.from({ length: count }, () => ({
      x: Math.random() * this.canvasW,
      y: Math.random() * this.canvasH,
      vx: (Math.random() - 0.5) * this.net.nodeSpeed,
      vy: (Math.random() - 0.5) * this.net.nodeSpeed,
      radius: 1.1 + Math.random() * 1.6,
      baseAlpha: 0.45 + Math.random() * 0.45,
      phase: Math.random() * Math.PI * 2,
    }));
    this.pulses = [];
    this.sparks = [];
  }

  private tick = () => {
    const now = performance.now();
    const dt = Math.min(60, now - this.lastTime) / 16.67;
    this.lastTime = now;
    const { canvasW: w, canvasH: h, ctx, net } = this;
    if (!ctx) return;

    ctx.clearRect(0, 0, w, h);

    // 1. Update nodes
    for (const n of this.nodes) {
      n.x += n.vx * dt;
      n.y += n.vy * dt;
      // Wrap
      if (n.x < -10)    n.x = w + 10;
      if (n.x > w + 10) n.x = -10;
      if (n.y < -10)    n.y = h + 10;
      if (n.y > h + 10) n.y = -10;
      // Mouse repulsion
      if (this.mouseActive) {
        const dx = n.x - this.mouseX, dy = n.y - this.mouseY;
        const d2 = dx * dx + dy * dy;
        const r = net.mouseRadius;
        if (d2 < r * r && d2 > 0.0001) {
          const d = Math.sqrt(d2);
          const f = (r - d) / r * 0.04;
          n.vx += (dx / d) * f;
          n.vy += (dy / d) * f;
        }
      }
      n.vx *= 0.992;
      n.vy *= 0.992;
      n.phase += 0.02;
    }

    // 2. Connections + spark spawning
    const max = net.linkDistance, max2 = max * max;
    ctx.lineWidth = 0.6;
    for (let i = 0; i < this.nodes.length; i++) {
      const a = this.nodes[i];
      for (let j = i + 1; j < this.nodes.length; j++) {
        const b = this.nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < max2) {
          const d = Math.sqrt(d2);
          const alpha = (1 - d / max) * 0.32;
          ctx.strokeStyle = net.colors.line + alpha + ')';
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
          if (Math.random() < net.sparkChance) {
            this.sparks.push({ from: a, to: b, t: 0, speed: 0.011 + Math.random() * 0.012 });
          }
        }
      }
    }

    // 3. Sparks
    for (const s of this.sparks) {
      s.t += s.speed * dt;
      if (s.t >= 1) continue;
      const x = s.from.x + (s.to.x - s.from.x) * s.t;
      const y = s.from.y + (s.to.y - s.from.y) * s.t;
      const trail = 0.10;
      const t2 = Math.max(0, s.t - trail);
      const x2 = s.from.x + (s.to.x - s.from.x) * t2;
      const y2 = s.from.y + (s.to.y - s.from.y) * t2;
      const grad = ctx.createLinearGradient(x2, y2, x, y);
      grad.addColorStop(0, net.colors.spark + '0)');
      grad.addColorStop(1, net.colors.spark + '0.95)');
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.fillStyle = net.colors.spark + '1)';
      ctx.beginPath();
      ctx.arc(x, y, 1.4, 0, Math.PI * 2);
      ctx.fill();
    }
    this.sparks = this.sparks.filter(s => s.t < 1);

    // 4. Pulses
    for (const p of this.pulses) {
      p.radius += p.speed * dt;
      p.life = 1 - p.radius / p.maxRadius;
      if (p.life <= 0) continue;
      ctx.strokeStyle = net.colors.pulse + (p.life * 0.4) + ')';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.stroke();
    }
    this.pulses = this.pulses.filter(p => p.life > 0);

    // 5. Draw nodes on top
    for (const n of this.nodes) {
      const breath = 0.85 + Math.sin(n.phase) * 0.15;
      const a = n.baseAlpha * breath;
      // Glow
      const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.radius * 7);
      grad.addColorStop(0,    net.colors.core + (a * 0.55) + ')');
      grad.addColorStop(0.45, net.colors.glow + (a * 0.12) + ')');
      grad.addColorStop(1,    'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius * 7, 0, Math.PI * 2);
      ctx.fill();
      // Core
      ctx.fillStyle = net.colors.core + a + ')';
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fill();
      // Random pulse spawn
      if (Math.random() < net.pulseChance) {
        this.pulses.push({
          x: n.x, y: n.y, radius: 0,
          maxRadius: 70 + Math.random() * 60, speed: 1.1, life: 1,
        });
      }
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
