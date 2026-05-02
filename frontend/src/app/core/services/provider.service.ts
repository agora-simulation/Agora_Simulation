import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import {
  Provider,
  ProviderCreate,
  ProviderUpdate,
  ProviderTestResult,
  Preset,
  CostEstimate,
  CostEstimateRequest,
} from '../models/provider.model';

@Injectable({ providedIn: 'root' })
export class ProviderService {
  private api = inject(ApiService);

  list(): Observable<Provider[]> {
    return this.api.get<Provider[]>('/providers/');
  }

  create(data: ProviderCreate): Observable<Provider> {
    return this.api.post<Provider>('/providers/', data);
  }

  get(id: string): Observable<Provider> {
    return this.api.get<Provider>(`/providers/${id}`);
  }

  update(id: string, data: ProviderUpdate): Observable<Provider> {
    return this.api.put<Provider>(`/providers/${id}`, data);
  }

  delete(id: string): Observable<void> {
    return this.api.delete(`/providers/${id}`);
  }

  test(id: string): Observable<ProviderTestResult> {
    return this.api.post<ProviderTestResult>(`/providers/${id}/test`);
  }

  getPresets(): Observable<Preset[]> {
    return this.api.get<Preset[]>('/providers/presets');
  }

  estimateCost(data: CostEstimateRequest): Observable<CostEstimate> {
    return this.api.post<CostEstimate>('/providers/estimate-cost', data);
  }
}
