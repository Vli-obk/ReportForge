import Header from '@/components/Header';
import Footer from '@/components/Footer';
import HeroSection from './components/HeroSection';
import CategoriesSection from './components/CategoriesSection';
import LeaderboardSection from './components/LeaderboardSection';
import CompatibilitySection from './components/CompatibilitySection';
import ProUnlockSection from './components/ProUnlockSection';
import StickyBar from './components/StickyBar';

export default function HomePage() {
  return (
    <div style={{ background: 'var(--carbon)', minHeight: '100vh' }} className="relative">
      <Header />
      <main className="relative z-10">
        <HeroSection />
        <CategoriesSection />
        <LeaderboardSection />
        <CompatibilitySection />
        <ProUnlockSection />
      </main>
      <Footer />
      <StickyBar />
    </div>
  );
}
