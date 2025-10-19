import '../app/globals.css';

interface SpaceSceneProps {
    className?: string;
}

export default function SpaceScene({ className = '' }: SpaceSceneProps) {
    return (
        <div className={`fixed inset-0 -z-10 overflow-hidden ${className}`}>
            <div className={`space-background ${className}`}>
                <div className="nebula"></div>
            </div>
        </div>
    );
}