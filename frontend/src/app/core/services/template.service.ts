import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { Template, TemplateCreate, TemplateCategory } from '../models/template.model';
import { PaginatedResponse } from '../models/api.model';

@Injectable({ providedIn: 'root' })
export class TemplateService {
  private api = inject(ApiService);

  list(params?: { category?: TemplateCategory; is_default?: boolean }): Observable<PaginatedResponse<Template>> {
    return this.api.get('/templates/', params as any);
  }

  getById(id: string): Observable<Template> {
    return this.api.get(`/templates/${id}`);
  }

  create(data: TemplateCreate): Observable<Template> {
    return this.api.post('/templates/', data);
  }

  update(id: string, data: Partial<TemplateCreate>): Observable<Template> {
    return this.api.put(`/templates/${id}`, data);
  }

  delete(id: string): Observable<void> {
    return this.api.delete(`/templates/${id}`);
  }

  seedDefaults(): Observable<any> {
    return this.api.post('/templates/seed-defaults');
  }

  getCategories(): Observable<string[]> {
    return this.api.get('/templates/categories');
  }
}
