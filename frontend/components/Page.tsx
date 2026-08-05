import { ReactNode } from "react";

export default function Page({ title, description, action, children, eyebrow = "OrgMemory" }: { title: string; description: string; action?: ReactNode; children: ReactNode; eyebrow?: string }) {
  return <div className="content">
    <div className="page-head"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p className="page-description">{description}</p></div>{action}</div>
    {children}
  </div>;
}
