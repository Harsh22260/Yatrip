import { useCallback, useEffect, useState } from "react";
import { getStoredUser, getUserProfile, hasSessionHint } from "../services/authService";

/**
 * Current user, from the cached profile first and then the live endpoint.
 *
 * There is no global auth context in this app: the navbar and the owner pages
 * each read the cache from `authService` and re-validate against `/profile/`.
 * This hook just gives that same pattern a name so pages stop re-implementing
 * it (and stop reaching for a `localStorage` token that no longer exists).
 *
 * The access token is an HttpOnly cookie, so the only synchronous signal
 * available on first render is the cached profile plus the session hint.
 */
export default function useCurrentUser() {
  const [user, setUser] = useState(() => getStoredUser());
  // True only when the profile is worth re-validating. An anonymous visitor has
  // no cookie hint and no cache, so there is nothing to fetch and nothing to wait
  // for. Deciding this at init is what keeps the mount effect free of setState.
  const [loading, setLoading] = useState(
    () => !getStoredUser() && (hasSessionHint() || Boolean(getStoredUser()))
  );

  const refresh = useCallback(async () => {
    try {
      // `getUserProfile` also writes the cache, so other pages see the result.
      const profile = await getUserProfile();
      setUser(profile);
      return profile;
    } catch {
      // A 401 here just means the cookie is gone or expired. Clear the stale
      // cache so the UI stops showing a signed-in shell for nobody.
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasSessionHint() && !getStoredUser()) {
      return undefined;
    }

    let active = true;
    getUserProfile()
      .then((profile) => { if (active) setUser(profile); })
      .catch(() => { if (active) setUser(null); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return {
    user,
    loading,
    isOwner: Boolean(user?.is_owner),
    refresh,
  };
}