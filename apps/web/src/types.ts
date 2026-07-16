export type Role = 'teacher' | 'student' | 'admin' | null;
export type WorkspaceRole = Exclude<Role, null>;

export interface Message {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  type?: 'text' | 'analysis' | 'quiz' | 'plan' | 'schedule';
  metadata?: any;
}

export interface Attachment {
  name: string;
  size: string;
  type: string;
}
