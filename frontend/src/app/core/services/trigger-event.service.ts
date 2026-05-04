import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { TriggerEvent, TriggerEventCreate } from '../models/trigger-event.model';

@Injectable({ providedIn: 'root' })
export class TriggerEventService {
  private api = inject(ApiService);

  list(simulationId: string): Observable<TriggerEvent[]> {
    return this.api.get('/trigger-events/', { simulation_id: simulationId } as any);
  }

  create(data: TriggerEventCreate): Observable<TriggerEvent> {
    return this.api.post('/trigger-events/', data);
  }

  update(id: string, data: Partial<TriggerEventCreate>): Observable<TriggerEvent> {
    return this.api.put(`/trigger-events/${id}`, data);
  }

  delete(id: string): Observable<void> {
    return this.api.delete(`/trigger-events/${id}`);
  }

  inject(simulationId: string, data: TriggerEventCreate): Observable<TriggerEvent> {
    return this.api.post(`/trigger-events/${simulationId}/inject`, data);
  }
}
