import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Simulation, SimulationCreate, SimulationStats, TickSnapshot } from '../models/simulation.model';
import { InfluenceEvent } from '../models/content.model';
import { PaginatedResponse } from '../models/api.model';

@Injectable({ providedIn: 'root' })
export class SimulationService {
  private api = inject(ApiService);

  list(params?: { limit?: number; offset?: number; status?: string; name?: string }): Observable<PaginatedResponse<Simulation>> {
    return this.api.get('/simulations/', params as Record<string, string | number>);
  }

  getById(id: string): Observable<Simulation> {
    return this.api.get(`/simulations/${id}`);
  }

  create(data: SimulationCreate): Observable<Simulation> {
    return this.api.post('/simulations/', data);
  }

  run(id: string): Observable<{ simulation_id: string; message: string }> {
    return this.api.post(`/simulations/${id}/run`);
  }

  cancel(id: string): Observable<{ simulation_id: string; message: string }> {
    return this.api.post(`/simulations/${id}/cancel`);
  }

  reset(id: string): Observable<{ simulation_id: string; message: string }> {
    return this.api.post(`/simulations/${id}/reset`);
  }

  clone(id: string): Observable<Simulation> {
    return this.api.post(`/simulations/${id}/clone`);
  }

  delete(id: string): Observable<void> {
    return this.api.delete(`/simulations/${id}`);
  }

  getStats(id: string): Observable<SimulationStats> {
    return this.api.get(`/simulations/${id}/stats`);
  }

  getTicks(id: string): Observable<TickSnapshot[]> {
    return this.api.get(`/simulations/${id}/ticks`);
  }

  getSentimentStats(id: string): Observable<any> {
    return this.api.get(`/simulations/${id}/sentiment-stats`);
  }

  getKpis(id: string): Observable<any> {
    return this.api.get(`/analysis/${id}/kpis`);
  }

  getNetworkMetrics(id: string): Observable<any> {
    return this.api.get(`/analysis/${id}/network-metrics`);
  }

  getMarketContext(id: string): Observable<any> {
    return this.api.get(`/simulations/${id}/market-context`);
  }

  updateMarketContext(id: string, data: any): Observable<any> {
    return this.api.put(`/simulations/${id}/market-context`, data);
  }

  approveResearch(id: string): Observable<{ simulation_id: string; message: string }> {
    return this.api.post(`/simulations/${id}/research/approve`);
  }

  getInfluenceEvents(id: string, params?: { ingame_day?: number; limit?: number }): Observable<InfluenceEvent[]> {
    return this.api.get(`/simulations/${id}/influence-events`, params as Record<string, string | number>);
  }
}
