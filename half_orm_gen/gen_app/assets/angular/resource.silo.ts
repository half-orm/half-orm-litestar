import { signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { catchError, filter, of, tap } from 'rxjs';
import { AuthService } from '../core/auth.service';
import { registerClear } from '../core/state-registry';
import { ResourceSchema } from './schema.types';

export type Row = Record<string, unknown>;

export class ResourceSilo {
  readonly items         = signal<Row[]>([]);
  readonly byId          = signal(new Map<string, Row>());
  readonly isLoading     = signal(false);
  readonly hasMore       = signal(true);
  readonly currentOffset = signal(0);

  readonly filters    = signal<Record<string, string>>({});
  readonly selectedId = signal<string | null>(null);
  readonly sortField  = signal<string | null>(null);
  readonly sortAsc    = signal(true);

  private loadedFilters = new Map<string, boolean>();
  private pk: string | null;

  constructor(
    readonly key: string,
    readonly schema: ResourceSchema,
    private baseUrl: string,
    private http: HttpClient,
    private auth: AuthService,
  ) {
    this.pk = schema.pk_fields.length === 1 ? schema.pk_fields[0] : null;
    registerClear(() => this.clear());
    this.auth.wsEvent$
      .pipe(filter(ev => ev.resource === key))
      .subscribe(ev => {
        if (ev.event === 'delete') this.removeItem(String(ev.id));
        else this.refresh(String(ev.id)).subscribe();
      });
  }

  private get headers(): HttpHeaders {
    const t = this.auth.token();
    return t ? new HttpHeaders({ Authorization: `Bearer ${t}` }) : new HttpHeaders();
  }

  pkValue(item: Row): string | null {
    return this.pk ? String(item[this.pk]) : null;
  }

  listUrl(params: Row = {}): string {
    const filtered = Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v != null && (typeof v !== 'string' || v !== ''))
        .map(([k, v]) => [`ho_col_${k}`, String(v)])
    );
    const qs = new URLSearchParams(filtered).toString();
    return qs ? `${this.baseUrl}?${qs}` : this.baseUrl;
  }

  getUrl(id: string): string { return `${this.baseUrl}/${id}`; }

  list(params: Row = {}, offset = 0): void {
    const filterKey = JSON.stringify(params);
    if (offset === 0 && this.loadedFilters.get(filterKey)) return;
    if (this.isLoading()) return;

    const searchQ = params['q'];
    const otherParams = searchQ ? {} : params;
    const baseUrl = this.listUrl(otherParams);
    const sep = baseUrl.includes('?') ? '&' : '?';
    const urlParams = new URLSearchParams();
    if (searchQ) urlParams.set('q', String(searchQ));
    if (offset > 0) urlParams.set('offset', String(offset));
    urlParams.set('limit', '100');
    const qs = urlParams.toString();
    const url = qs ? `${baseUrl}${sep}${qs}` : baseUrl;
    if (this.auth.fetchedRoutes.has(url)) return;
    this.auth.fetchedRoutes.add(url);

    this.isLoading.set(true);
    this.http.get<{ data: Row[]; meta: { offset: number; limit: number; has_more: boolean } }>(
      url, { headers: this.headers }
    ).pipe(
      catchError(() => of({ data: [], meta: { offset, limit: 100, has_more: false } }))
    ).subscribe(response => {
      if (offset === 0 && !searchQ && Object.keys(params).length === 0) this.setItems(response.data);
      else this.mergeItems(response.data);
      this.hasMore.set(response.meta.has_more);
      this.currentOffset.set(offset + response.data.length);
      this.isLoading.set(false);
      if (!response.meta.has_more) this.loadedFilters.set(filterKey, true);
    });
  }

  loadMore(params: Row = {}): void {
    if (!this.hasMore() || this.isLoading()) return;
    this.list(params, this.currentOffset());
  }

  resetFilterState(): void {
    this.loadedFilters.clear();
    this.hasMore.set(true);
    this.currentOffset.set(0);
  }

  get(id: string) {
    const cached = this.byId().get(id);
    if (cached) return of(cached);
    return this.refresh(id);
  }

  refresh(id: string) {
    const url = this.getUrl(id);
    this.auth.fetchedRoutes.add(url);
    return this.http.get<Row>(url, { headers: this.headers }).pipe(
      tap(item => this.setItem(item)),
      catchError(() => of(null as Row | null))
    );
  }

  create(data: Row) {
    return this.http.post<Row>(this.baseUrl, data, {
      headers: this.headers.append('Content-Type', 'application/json'),
    });
  }

  update(id: string, data: Row) {
    return this.http.put<Row>(`${this.baseUrl}/${id}`, data, {
      headers: this.headers.append('Content-Type', 'application/json'),
    });
  }

  remove(id: string) {
    return this.http.delete(`${this.baseUrl}/${id}`, { headers: this.headers });
  }

  private setItems(items: Row[]): void {
    this.items.set(items);
    if (this.pk) {
      const pk = this.pk;
      this.byId.set(new Map(items.map(i => [String(i[pk]), i])));
    }
  }

  private mergeItems(newItems: Row[]): void {
    if (!this.pk) {
      this.items.set([...this.items(), ...newItems]);
      return;
    }
    const pk = this.pk;
    const map = new Map(this.byId());
    for (const item of newItems) map.set(String(item[pk]), item);
    this.byId.set(map);
    this.items.set([...map.values()]);
  }

  setItem(item: Row): void {
    if (!this.pk) return;
    const pk = this.pk;
    const id = String(item[pk]);
    const map = new Map(this.byId());
    map.set(id, item);
    this.byId.set(map);
    this.items.update(items => {
      const idx = items.findIndex(i => String(i[pk]) === id);
      if (idx >= 0) { const next = [...items]; next[idx] = item; return next; }
      return [...items, item];
    });
  }

  removeItem(id: string): void {
    if (!this.pk) return;
    const pk = this.pk;
    const map = new Map(this.byId());
    map.delete(id);
    this.byId.set(map);
    this.items.update(items => items.filter(i => String(i[pk]) !== id));
  }

  clear(): void {
    this.items.set([]);
    this.byId.set(new Map());
    this.loadedFilters.clear();
    this.hasMore.set(true);
    this.currentOffset.set(0);
  }
}