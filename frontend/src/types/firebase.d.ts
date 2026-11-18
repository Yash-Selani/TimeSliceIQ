/* eslint-disable @typescript-eslint/no-explicit-any */
declare module 'firebase/app' {
  export interface FirebaseApp {
    name: string;
    options: Record<string, any>;
  }
  export function initializeApp(options: Record<string, any>): FirebaseApp;
  export function getApps(): FirebaseApp[];
}

declare module 'firebase/auth' {
  export interface User {
    uid: string;
    email: string | null;
    displayName: string | null;
    photoURL: string | null;
  }
  export interface Auth {
    currentUser: User | null;
  }
  export class GoogleAuthProvider {
    setCustomParameters(params: Record<string, string>): void;
  }
  export function getAuth(app?: any): Auth;
  export function onAuthStateChanged(auth: Auth, callback: (user: User | null) => void): () => void;
  export function signInWithPopup(auth: Auth, provider: any): Promise<any>;
  export function signInWithRedirect(auth: Auth, provider: any): Promise<void>;
  export function getRedirectResult(auth: Auth): Promise<any>;
  export function signInWithEmailAndPassword(auth: Auth, email: string, pass: string): Promise<any>;
  export function createUserWithEmailAndPassword(auth: Auth, email: string, pass: string): Promise<any>;
  export function signOut(auth: Auth): Promise<void>;
}

declare module 'firebase/firestore' {
  export interface Firestore {
    type: string;
  }
  export function getFirestore(app?: any): Firestore;
  export function collection(db: Firestore, ...pathSegments: string[]): any;
  export function doc(db: Firestore, ...pathSegments: string[]): any;
  export function setDoc(docRef: any, data: any, options?: { merge?: boolean }): Promise<void>;
  export function getDoc(docRef: any): Promise<any>;
  export function getDocs(queryRef: any): Promise<any>;
  export function deleteDoc(docRef: any): Promise<void>;
  export function query(collectionRef: any, ...queryConstraints: any[]): any;
  export function orderBy(fieldPath: string, directionStr?: string): any;
  export function limit(limitNum: number): any;
}
