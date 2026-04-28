import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Member {
  member_number: number;
  membership_id: string;
  name: string;
  expiration_date: string;
  has_face_sample: boolean;
}

export interface RecognitionResult {
  recognized: boolean;
  member_number?: number;
  membership_id?: string;
  name?: string;
  confidence?: number;
  access_granted?: boolean;
  expiration_date?: string;
  message: string;
}

export interface Stats {
  total_members: number;
  active_members: number;
  expired_members: number;
  entries_today: number;
  entries_this_week: number;
}

export interface AttendanceRecord {
  id: number;
  member_number: number;
  membership_id: string;
  name: string;
  date: string;
  time: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = '/api';

  getMembers(): Observable<Member[]> {
    return this.http.get<Member[]>(`${this.baseUrl}/members`);
  }

  getMember(id: string): Observable<Member> {
    return this.http.get<Member>(`${this.baseUrl}/members/${id}`);
  }

  registerMember(member: { name: string; expiration_date: string }): Observable<Member> {
    return this.http.post<Member>(`${this.baseUrl}/members`, member);
  }

  updateMember(id: string, member: Partial<Member>): Observable<Member> {
    return this.http.put<Member>(`${this.baseUrl}/members/${id}`, member);
  }

  deleteMember(id: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/members/${id}`);
  }

  uploadFace(id: string, imageBase64: string): Observable<Member> {
    return this.http.post<Member>(`${this.baseUrl}/members/${id}/face`, { image: imageBase64 });
  }

  recognize(imageBase64: string): Observable<RecognitionResult> {
    return this.http.post<RecognitionResult>(`${this.baseUrl}/recognize`, { image: imageBase64 });
  }

  getStats(): Observable<Stats> {
    return this.http.get<Stats>(`${this.baseUrl}/stats`);
  }

  getAttendance(): Observable<AttendanceRecord[]> {
    return this.http.get<AttendanceRecord[]>(`${this.baseUrl}/attendance`);
  }
}
