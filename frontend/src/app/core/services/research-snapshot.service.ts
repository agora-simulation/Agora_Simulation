import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { ResearchSnapshot, ResearchSnapshotCreate, ResearchExecuteRequest } from '../models/research-snapshot.model';
import { PaginatedResponse } from '../models/api.model';

@Injectable({ providedIn: 'root' })
export class ResearchSnapshotService {
  private api = inject(ApiService);

  list(params?: { status?: string }): Observable<PaginatedResponse<ResearchSnapshot>> {
    return this.api.get('/research/', params as any);
  }

  getById(id: string): Observable<ResearchSnapshot> {
    return this.api.get(`/research/${id}`);
  }

  create(data: ResearchSnapshotCreate): Observable<ResearchSnapshot> {
    return this.api.post('/research/', data);
  }

  update(id: string, data: Partial<ResearchSnapshot>): Observable<ResearchSnapshot> {
    return this.api.put(`/research/${id}`, data);
  }

  delete(id: string): Observable<void> {
    return this.api.delete(`/research/${id}`);
  }

  approve(id: string): Observable<ResearchSnapshot> {
    return this.api.post(`/research/${id}/approve`);
  }

  execute(id: string, data?: ResearchExecuteRequest): Observable<ResearchSnapshot> {
    return this.api.post(`/research/${id}/execute`, data || {});
  }
}
