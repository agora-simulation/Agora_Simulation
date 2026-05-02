import { Directive, ElementRef, HostListener, inject } from '@angular/core';

/**
 * Mouse-tracking glow effect for cards.
 * Adds a radial spotlight that follows the cursor.
 *
 * Usage: <div class="card" appCardGlow>...</div>
 */
@Directive({
  selector: '[appCardGlow]',
  standalone: true,
})
export class CardGlowDirective {
  private el = inject(ElementRef<HTMLElement>);

  @HostListener('mousemove', ['$event'])
  onMouseMove(e: MouseEvent) {
    const rect = this.el.nativeElement.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    this.el.nativeElement.style.setProperty('--glow-x', `${x}px`);
    this.el.nativeElement.style.setProperty('--glow-y', `${y}px`);
    this.el.nativeElement.style.setProperty('--glow-opacity', '1');
  }

  @HostListener('mouseleave')
  onMouseLeave() {
    this.el.nativeElement.style.setProperty('--glow-opacity', '0');
  }
}
