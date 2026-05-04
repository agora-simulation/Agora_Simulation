import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { SimPlatform, PlatformCreate } from '../models/platform.model';

@Injectable({ providedIn: 'root' })
export class PlatformService {
  private api = inject(ApiService);

  list(simulationId?: string): Observable<SimPlatform[]> {
    const params = simulationId ? { simulation_id: simulationId } : {};
    return this.api.get('/platforms/', params as any);
  }

  getById(id: string): Observable<SimPlatform> {
    return this.api.get(`/platforms/${id}`);
  }

  create(data: PlatformCreate): Observable<SimPlatform> {
    return this.api.post('/platforms/', data);
  }

  update(id: string, data: Partial<PlatformCreate> & { is_active?: boolean }): Observable<SimPlatform> {
    return this.api.put(`/platforms/${id}`, data);
  }

  delete(id: string): Observable<void> {
    return this.api.delete(`/platforms/${id}`);
  }

  seedDefaults(): Observable<any> {
    return this.api.post('/platforms/seed-defaults');
  }
}
