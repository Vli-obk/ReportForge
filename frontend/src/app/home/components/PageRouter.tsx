'use client';

import { usePathname } from 'next/navigation';
import DashboardLayout from './DashboardLayout';
import DashboardPageContent from './DashboardPage';
import UploadsPageContent from './UploadsPage';
import DatasetsPageContent from './DatasetsPage';
import AnalyticsPageContent from './AnalyticsPage';
import PipelinePageContent from './PipelinePage';
import SettingsPageContent from './SettingsPage';

export default function PageRouter() {
  const pathname = usePathname();

  // Render dashboard pages
  if (pathname?.startsWith('/home/dashboard')) {
    return (
      <DashboardLayout>
        <DashboardPageContent />
      </DashboardLayout>
    );
  }

  if (pathname?.startsWith('/home/uploads')) {
    return (
      <DashboardLayout>
        <UploadsPageContent />
      </DashboardLayout>
    );
  }

  if (pathname?.startsWith('/home/datasets')) {
    return (
      <DashboardLayout>
        <DatasetsPageContent />
      </DashboardLayout>
    );
  }

  if (pathname?.startsWith('/home/analytics')) {
    return (
      <DashboardLayout>
        <AnalyticsPageContent />
      </DashboardLayout>
    );
  }

  if (pathname?.startsWith('/home/pipeline')) {
    return (
      <DashboardLayout>
        <PipelinePageContent />
      </DashboardLayout>
    );
  }

  if (pathname?.startsWith('/home/settings')) {
    return (
      <DashboardLayout>
        <SettingsPageContent />
      </DashboardLayout>
    );
  }

  // Default - should not reach here
  return <div>Page not found</div>;
}
