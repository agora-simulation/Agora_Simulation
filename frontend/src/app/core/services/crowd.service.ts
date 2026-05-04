import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { CrowdState } from '../models/crowd.model';

@Injectable({ providedIn: 'root' })
export class CrowdService {
  private api = inject(ApiService);

  getAll(simulationId: string): Observable<CrowdState[]> {
    return this.api.get(`/crowd/${simulationId}`);
  }

  getLatest(simulationId: string): Observable<CrowdState> {
    return this.api.get(`/crowd/${simulationId}/latest`);
  }

  getByPlatform(simulationId: string, platformId: string): Observable<CrowdState[]> {
    return this.api.get(`/crowd/${simulationId}/platform/${platformId}`);
  }
}
